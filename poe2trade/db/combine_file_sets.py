from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from poe2trade import poe2trade_root
from poe2trade.db.league_paths import file_sets_root as active_file_sets_root
from poe2trade.db.league_paths import files_root as active_files_root


FILE_SETS_ROOT = Path(poe2trade_root) / "db" / "file_sets_to_combine"
FILES_ROOT = Path(poe2trade_root) / "db" / "files"


@dataclass(frozen=True)
class CopyPlanEntry:
    src: Path
    category: str
    filename: str

    @property
    def destination_key(self) -> tuple[str, str]:
        return (self.category, self.filename)


def _is_runeforged_json(path: Path) -> bool:
    return path.name.lower().startswith("runeforged_")


def _build_copy_plan(
    file_sets_root: Path,
    skip_runeforged: bool = True,
) -> tuple[list[CopyPlanEntry], int]:
    if not file_sets_root.is_dir():
        raise FileNotFoundError(f"File sets directory not found: {file_sets_root}")

    set_dirs = sorted(path for path in file_sets_root.iterdir() if path.is_dir())
    if not set_dirs:
        raise ValueError(f"No file set directories found in: {file_sets_root}")

    plan: list[CopyPlanEntry] = []
    seen: dict[tuple[str, str], Path] = {}
    skipped_runeforged = 0

    for set_dir in set_dirs:
        category_dirs = sorted(path for path in set_dir.iterdir() if path.is_dir())
        for category_dir in category_dirs:
            category = category_dir.name
            for child in sorted(category_dir.iterdir()):
                if child.is_dir():
                    raise ValueError(f"Unexpected nested directory in category set: {child}")
                if child.suffix.lower() != ".json":
                    raise ValueError(f"Unexpected non-JSON file in category set: {child}")
                if skip_runeforged and _is_runeforged_json(child):
                    skipped_runeforged += 1
                    continue

                entry = CopyPlanEntry(src=child, category=category, filename=child.name)
                duplicate = seen.get(entry.destination_key)
                if duplicate is not None:
                    category_name, filename = entry.destination_key
                    raise ValueError(
                        "Duplicate destination JSON for "
                        f"{category_name}/{filename}: {duplicate} and {child}"
                    )
                seen[entry.destination_key] = child
                plan.append(entry)

    if not plan:
        raise ValueError(f"No JSON files found in file sets directory: {file_sets_root}")

    return plan, skipped_runeforged


def combine_file_sets(
    file_sets_root: Path = FILE_SETS_ROOT,
    files_root: Path = FILES_ROOT,
    skip_runeforged: bool = True,
) -> list[str]:
    """Rebuild db/files category directories from file_sets_to_combine."""
    file_sets_root = Path(file_sets_root)
    files_root = Path(files_root)
    plan, skipped_runeforged = _build_copy_plan(file_sets_root, skip_runeforged=skip_runeforged)
    categories = sorted({entry.category for entry in plan})

    files_root.mkdir(parents=True, exist_ok=True)
    for child in sorted(files_root.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)

    for entry in plan:
        dst_dir = files_root / entry.category
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry.src, dst_dir / entry.filename)

    print(
        f"Combined {len(plan)} JSON files across {len(categories)} categories into {files_root}"
    )
    if skipped_runeforged:
        print(f"  - Skipped {skipped_runeforged} Runeforged JSON file(s).")
    for category in categories:
        count = sum(1 for entry in plan if entry.category == category)
        print(f"  - {category}: {count} JSON files")

    return categories


def main(
    _categories: list[str] | None = None,
    skip_runeforged: bool = True,
) -> list[str]:
    return combine_file_sets(
        file_sets_root=active_file_sets_root(),
        files_root=active_files_root(),
        skip_runeforged=skip_runeforged,
    )
