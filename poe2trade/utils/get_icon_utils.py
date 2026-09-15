"""Build and validate the base-item icon manifest used at runtime.

The release pipeline packages ``db/files/base_images.json`` and
``db/base_icons`` into the portable app, then mirrors them to the serve repo.
This module keeps that manifest derived from the current item datasets instead
of a hand-maintained category list.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Iterable

import requests

from poe2trade import poe2trade_root

TARGET_DIR = Path(poe2trade_root) / "db" / "files"
OUTPUT_PATH = TARGET_DIR / "base_images.json"
IMAGE_OUTPUT_ROOT = Path(poe2trade_root) / "db" / "base_icons"


def discover_category_dirs(files_root: Path) -> list[str]:
    """Return dataset category directories that contain item JSON files."""

    if not files_root.is_dir():
        return []
    categories: list[str] = []
    for path in files_root.iterdir():
        if path.is_dir() and any(path.rglob("*.json")):
            categories.append(path.name)
    return sorted(categories, key=str.casefold)


def find_json_files(files_root: Path, categories: Iterable[str] | None = None) -> list[tuple[Path, str]]:
    """Return ``(json_path, category)`` pairs under the dataset root."""

    selected = list(categories) if categories is not None else discover_category_dirs(files_root)
    json_files: list[tuple[Path, str]] = []
    for category in selected:
        category_dir = files_root / category
        if not category_dir.is_dir():
            continue
        for file_path in sorted(category_dir.rglob("*.json"), key=lambda p: p.as_posix().casefold()):
            json_files.append((file_path, category))
    return json_files


def extract_unique_items(json_files: Iterable[tuple[Path, str]]) -> list[dict[str, str]]:
    """Extract the sorted unique ``baseType``/``icon``/``category`` rows."""

    unique: set[tuple[str, str, str]] = set()
    for file_path, category in json_files:
        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            continue
        for record in data:
            item = record.get("item") if isinstance(record, dict) else None
            if not isinstance(item, dict):
                continue
            base_type = str(item.get("baseType") or "").strip()
            icon = str(item.get("icon") or "").strip()
            if base_type and icon:
                unique.add((base_type, icon, category))

    return [
        {"baseType": base_type, "icon": icon, "category": category}
        for base_type, icon, category in sorted(
            unique, key=lambda row: (row[2].casefold(), row[0].casefold(), row[1])
        )
    ]


def merge_base_images(
    existing: Iterable[dict[str, str]], scanned: Iterable[dict[str, str]]
) -> list[dict[str, str]]:
    """Union the icon store with a fresh scan, keyed by base type and category.

    The store is shared by every league the app ships, but the scan only sees
    the raw data of whichever league was scraped last. Replacing the file
    therefore deleted base types that exist only in another league -- the
    Runeforged shields and bucklers of Runes of Aldur vanished the moment the
    dataset held Forbidden Rites, while its models were still being shipped.

    Icons are small and stable, so retaining them costs almost nothing and
    losing one means an item renders without art. A base type present in the
    scan takes the scanned icon, so a genuine art change still lands.

    The key folds the category's case. Upstream flip-flops the casing it emits
    for a dataset directory -- one scrape wrote ``Body_Armour``, the next
    ``body_armour`` -- and a case-sensitive key turned each flip into a second
    entry per base type instead of an update, growing the manifest by 187
    duplicate rows. The scanned row still supplies the surviving casing, so a
    rebuild re-canonicalises the store onto whatever the datasets emit now.
    """
    merged: dict[tuple[str, str], dict[str, str]] = {}
    for row in list(existing) + list(scanned):
        base_type = str(row.get("baseType") or "").strip()
        icon = str(row.get("icon") or "").strip()
        category = str(row.get("category") or "").strip()
        if base_type and icon and category:
            merged[(base_type, category.casefold())] = {
                "baseType": base_type, "icon": icon, "category": category,
            }
    # key[1] is already casefolded, so the sort is on the folded category.
    return [merged[key] for key in sorted(merged, key=lambda k: (k[1], k[0].casefold()))]


def save_to_json(data: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[DONE] Saved {len(data)} unique entries to {output_path}")


def load_base_images(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list")
    return [
        {
            "baseType": str(item.get("baseType") or ""),
            "icon": str(item.get("icon") or ""),
            "category": str(item.get("category") or ""),
        }
        for item in data
        if isinstance(item, dict)
    ]


def sanitize_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).rstrip()


def icon_path_for(entry: dict[str, str], output_root: Path) -> Path:
    return output_root / entry["category"] / f"{sanitize_filename(entry['baseType'])}.png"


def download_images(
    data: Iterable[dict[str, str]],
    output_root: Path,
    *,
    session=requests,
    timeout: int = 10,
) -> list[Path]:
    """Download missing icon PNGs and return the paths written."""

    written: list[Path] = []
    print("[INFO] Starting image downloads...")
    for entry in data:
        image_path = icon_path_for(entry, output_root)
        image_path.parent.mkdir(parents=True, exist_ok=True)
        if image_path.exists():
            print(f"[SKIP] Already exists: {image_path}")
            continue

        icon_url = entry["icon"]
        try:
            response = session.get(icon_url, timeout=timeout)
            if response.status_code != 200:
                print(f"[ERROR] Failed to download {icon_url}: status {response.status_code}")
                continue
            image_path.write_bytes(response.content)
            written.append(image_path)
            print(f"[DOWNLOADED] {image_path}")
        except Exception as exc:
            print(f"[ERROR] Exception downloading {icon_url}: {exc}")
    return written


def assign_default_icons(output_root: Path, categories: Iterable[str]) -> list[Path]:
    """Copy the first sorted category PNG to ``default.png`` deterministically."""

    written: list[Path] = []
    print("[INFO] Assigning default icons...")
    for category in sorted(set(categories), key=str.casefold):
        category_path = output_root / category
        if not category_path.is_dir():
            print(f"[WARN] No folder found for {category}, skipping.")
            continue
        png_files = sorted(
            (path for path in category_path.glob("*.png") if path.name != "default.png"),
            key=lambda p: p.name.casefold(),
        )
        if not png_files:
            print(f"[WARN] No PNG files found in {category_path}, skipping.")
            continue

        chosen_path = png_files[0]
        default_path = category_path / "default.png"
        if not default_path.exists() or default_path.read_bytes() != chosen_path.read_bytes():
            shutil.copyfile(chosen_path, default_path)
            written.append(default_path)
        print(f"[DEFAULT] Assigned {chosen_path.name} as default for {category}")
    return written


def manifest_diff(
    expected: Iterable[dict[str, str]], actual: Iterable[dict[str, str]]
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Compare by base type and category -- the identity an icon file has.

    icon_path_for writes one PNG per (category, baseType), so several icon
    URLs for the same base type all resolve to the same file and only the last
    download survives. Keying on the URL as well reported those redundant rows
    as missing from a manifest that had in fact stored the base type.
    """

    def keyset(rows: Iterable[dict[str, str]]) -> set[tuple[str, str]]:
        return {
            (row.get("baseType", ""), row.get("category", ""))
            for row in rows
            if row.get("baseType") and row.get("icon") and row.get("category")
        }

    expected_keys = keyset(expected)
    actual_keys = keyset(actual)
    return sorted(expected_keys - actual_keys), sorted(actual_keys - expected_keys)


def missing_icon_paths(data: Iterable[dict[str, str]], output_root: Path) -> list[Path]:
    return [path for path in (icon_path_for(entry, output_root) for entry in data) if not path.exists()]


def missing_default_paths(data: Iterable[dict[str, str]], output_root: Path) -> list[Path]:
    categories = sorted({entry["category"] for entry in data if entry.get("category")}, key=str.casefold)
    return [output_root / category / "default.png" for category in categories if not (output_root / category / "default.png").exists()]


def check_manifest(files_root: Path, manifest_path: Path, icons_root: Path) -> list[str]:
    expected = extract_unique_items(find_json_files(files_root))
    errors: list[str] = []
    try:
        actual = load_base_images(manifest_path)
    except Exception as exc:
        return [f"could not read {manifest_path}: {exc}"]

    missing, extra = manifest_diff(expected, actual)
    if missing:
        errors.append(f"{len(missing)} dataset icon entries are missing from {manifest_path}")
    # Entries the current dataset does not contain are retained on purpose:
    # the store is shared across leagues and the scan only sees the one that
    # was scraped last. Reported, never an error.
    if extra:
        print(f"[INFO] {len(extra)} icon entry(ies) in {manifest_path.name} are not in "
              "this dataset; retained for other leagues.")

    missing_icons = missing_icon_paths(actual, icons_root)
    if missing_icons:
        errors.append(f"{len(missing_icons)} icon PNG files are missing under {icons_root}")

    missing_defaults = missing_default_paths(actual, icons_root)
    if missing_defaults:
        errors.append(f"{len(missing_defaults)} category default icons are missing under {icons_root}")

    return errors


def build_manifest(files_root: Path, manifest_path: Path, icons_root: Path, *, skip_download: bool = False) -> int:
    print(f"[INFO] Starting scan in: {files_root}")
    json_files = find_json_files(files_root)
    print(f"[INFO] Found {len(json_files)} JSON files to process.")
    scanned = extract_unique_items(json_files)
    try:
        existing = load_base_images(manifest_path)
    except (OSError, ValueError):
        existing = []
    data = merge_base_images(existing, scanned)
    retained = len(data) - len(scanned)
    if retained > 0:
        print(f"[INFO] Kept {retained} icon entry(ies) not in this dataset "
              "(base types from other leagues).")
    save_to_json(data, manifest_path)
    if not skip_download:
        download_images(data, icons_root)
    assign_default_icons(icons_root, [entry["category"] for entry in data])
    return len(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files-root", default=str(TARGET_DIR))
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    parser.add_argument("--icons-root", default=str(IMAGE_OUTPUT_ROOT))
    parser.add_argument("--check", action="store_true", help="Validate existing manifest/icons and exit.")
    parser.add_argument("--skip-download", action="store_true", help="Write the manifest/defaults without downloading missing icons.")
    args = parser.parse_args(argv)

    files_root = Path(args.files_root)
    output = Path(args.output)
    icons_root = Path(args.icons_root)

    if args.check:
        errors = check_manifest(files_root, output, icons_root)
        if errors:
            for error in errors:
                print(f"[ERROR] {error}")
            return 1
        print("[OK] base image manifest and icon files match the datasets")
        return 0

    count = build_manifest(files_root, output, icons_root, skip_download=args.skip_download)
    print(f"[OK] base image manifest contains {count} dataset-derived entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
