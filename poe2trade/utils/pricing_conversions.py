"""Co-versioned pricing conversion metadata for training and inference."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from poe2trade import chaos_exalt, divine_exalt, poe2trade_root

MANIFEST_NAME = "currency_conversions.json"
MODEL_SIDECAR_SUFFIX = ".pricing.json"
SCRAPE_SNAPSHOT_NAME = ".currency_conversions"
SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def conversion_manifest_from_snapshot(snapshot: Any) -> dict[str, Any]:
    """Build matrix metadata from the exact validated runtime snapshot."""
    return validate_conversion_manifest({
        "schema_version": SCHEMA_VERSION,
        "target_currency": "exalted",
        "exalted_to_exalt": float(snapshot.exalted),
        "chaos_to_exalt": float(snapshot.chaos),
        "divine_to_exalt": float(snapshot.divine),
        "league": str(snapshot.league),
        "source": str(snapshot.source),
        "refreshed_at": snapshot.fetched_at,
        "captured_at": _now_iso(),
    })


def current_conversion_manifest() -> dict[str, Any]:
    """Describe the rates currently used by matrix price conversion."""
    # A league training run persists one validated snapshot before any stage
    # starts. Always read that file so arithmetic and artifact metadata cannot
    # observe different refreshes of the process-wide conversion singleton.
    training_path = os.environ.get("POE2TRADE_TRAINING_CONVERSIONS", "").strip()
    if training_path:
        manifest = read_conversion_manifest(training_path)
        expected = os.environ.get("POE_LEAGUE", "").strip()
        actual = str(manifest.get("league") or "").strip()
        if expected and actual.casefold() != expected.casefold():
            raise RuntimeError(
                f"training conversion manifest is for {actual!r}, expected {expected!r}"
            )
        return manifest

    provenance: dict[str, Any] = {}
    rates_path = Path(poe2trade_root) / "data" / "rates.json"
    try:
        raw = json.loads(rates_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            provenance = {
                key: raw[key]
                for key in ("league", "source", "refreshed_at")
                if raw.get(key) not in (None, "")
            }
    except (OSError, ValueError, TypeError):
        provenance = {"source": "package_fallback"}

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "target_currency": "exalted",
        "exalted_to_exalt": 1.0,
        "chaos_to_exalt": float(chaos_exalt),
        "divine_to_exalt": float(divine_exalt),
        # Backward-compatible names used by the training package.
        "chaos_exalt": float(chaos_exalt),
        "divine_exalt": float(divine_exalt),
        "display": (
            f"1d = {float(divine_exalt):g}e, "
            f"1c = {float(chaos_exalt):g}e"
        ),
        "captured_at": _now_iso(),
    }
    manifest.update(provenance)
    return manifest


def scrape_conversion_manifest(category_dir: str | Path) -> dict[str, Any] | None:
    """Convert one category's scrape-time snapshot into matrix-rate metadata.

    Listings retain their native currency.  A sweep can span hours, so matrix
    conversion must prefer the rate snapshot beside the raw listings over the
    mutable package-wide ``data/rates.json`` used for new scrapes.
    """
    path = Path(category_dir) / SCRAPE_SNAPSHOT_NAME
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        rates = snapshot["rates"]
        chaos = float(rates["chaos"])
        divine = float(rates["divine"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
    if chaos <= 0 or divine <= 0:
        return None
    return validate_conversion_manifest({
        "schema_version": SCHEMA_VERSION,
        "target_currency": "exalted",
        "exalted_to_exalt": 1.0,
        "chaos_to_exalt": chaos,
        "divine_to_exalt": divine,
        "chaos_exalt": chaos,
        "divine_exalt": divine,
        "league": snapshot.get("league"),
        "source": snapshot.get("source") or "scrape_snapshot",
        "scrape_snapshot": path.name,
        "scrape_captured_at": snapshot.get("captured_at"),
        "scrape_run_id": snapshot.get("run_id"),
    })


def training_manifest_from_scrape_snapshots(
    files_dir: str | Path,
    category_folders: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build an immutable manifest from one or more copied category snapshots.

    ``category_folders`` scopes a training invocation to its raw input
    folders.  A caller training more than one folder still must supply a
    common snapshot; category-at-a-time callers keep each category's own
    scrape-time rates.
    """
    snapshots = sorted(Path(files_dir).glob(f"*/{SCRAPE_SNAPSHOT_NAME}"))
    if category_folders is not None:
        requested = {str(folder).casefold() for folder in category_folders}
        snapshots = [path for path in snapshots if path.parent.name.casefold() in requested]
    manifests = [scrape_conversion_manifest(path.parent) for path in snapshots]
    manifests = [manifest for manifest in manifests if manifest is not None]
    if not manifests:
        raise RuntimeError(f"no valid scrape-time conversion snapshots in {files_dir}")
    first = manifests[0]
    identity = (first["league"], first["chaos_to_exalt"], first["divine_to_exalt"])
    if any((m["league"], m["chaos_to_exalt"], m["divine_to_exalt"]) != identity for m in manifests[1:]):
        raise RuntimeError("scrape-time conversion snapshots disagree; split the training batch by rate snapshot")
    first["snapshot_categories"] = len(manifests)
    return first


def validate_conversion_manifest(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("currency conversion manifest must be an object")
    required = ("chaos_to_exalt", "divine_to_exalt")
    # Old sidecars remain readable, but only supported rates reach new payloads.
    supported = {"schema_version", "target_currency", "exalted_to_exalt",
                 "chaos_to_exalt", "divine_to_exalt", "chaos_exalt", "divine_exalt"}
    normalized = {key: value for key, value in data.items()
                  if key in supported or not (key.endswith("_to_exalt") or key.endswith("_exalt"))}
    normalized.pop("display", None)
    for key in required:
        value = float(normalized[key])
        if value <= 0:
            raise ValueError(f"{key} must be positive")
        normalized[key] = value
    normalized.setdefault("schema_version", SCHEMA_VERSION)
    normalized.setdefault("target_currency", "exalted")
    normalized.setdefault("exalted_to_exalt", 1.0)
    normalized.setdefault("chaos_exalt", normalized["chaos_to_exalt"])
    normalized.setdefault("divine_exalt", normalized["divine_to_exalt"])
    normalized.setdefault(
        "display",
        (
            f"1d = {normalized['divine_to_exalt']:g}e, "
            f"1c = {normalized['chaos_to_exalt']:g}e"
        ),
    )
    return normalized


def read_conversion_manifest(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_conversion_manifest(data)


def write_conversion_manifest(path: str | Path, data: dict[str, Any] | None = None) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = validate_conversion_manifest(data or current_conversion_manifest())
    tmp = target.with_name(f"{target.name}.tmp-{os.getpid()}-{uuid4().hex}")
    try:
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, target)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
    return target


def matrix_conversion_path(matrix_file: str | Path) -> Path:
    return Path(matrix_file).with_suffix(".pricing.json")


def model_conversion_path(model_file: str | Path) -> Path:
    return Path(model_file).with_suffix(MODEL_SIDECAR_SUFFIX)


def publish_model_conversions(matrix_file: str | Path, model_file: str | Path) -> Path:
    """Copy matrix-time rates beside one exact trained model pickle."""
    source = matrix_conversion_path(matrix_file)
    try:
        manifest = read_conversion_manifest(source)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        manifest = current_conversion_manifest()
        manifest["source_note"] = "matrix pricing sidecar missing; captured at training time"
    manifest["trained_at"] = _now_iso()
    manifest["matrix_file"] = Path(matrix_file).name
    manifest["model_file"] = Path(model_file).name
    return write_conversion_manifest(model_conversion_path(model_file), manifest)


def load_model_conversions(
    model_file: str | Path,
    fallback_dirs: Iterable[str | Path] = (),
) -> dict[str, Any]:
    """Read one model's sidecar on every prediction, with legacy fallbacks."""
    candidate = model_conversion_path(model_file)
    try:
        return read_conversion_manifest(candidate)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        pass

    # Compatibility for model sets published before per-model sidecars.
    for model_dir in fallback_dirs:
        candidate = Path(model_dir) / MANIFEST_NAME
        try:
            return read_conversion_manifest(candidate)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
    fallback = current_conversion_manifest()
    fallback["source_note"] = (
        f"pricing sidecar missing for {Path(model_file).name}; using runtime conversions"
    )
    return fallback
