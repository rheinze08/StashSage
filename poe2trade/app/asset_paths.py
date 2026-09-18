"""Resolve ``db/<name>`` asset directories with a writable per-user override.

Models and data (``super_models``, ``unsuper_models``, ``files``,
``base_icons``) are bundled inside the frozen package, but the in-app updater
drops server-fetched copies into ``%APPDATA%/StashSage/generated/<name>``. At
runtime the override copy wins so assets can be refreshed without reinstalling;
when no override exists the bundled copy is used. This keeps the app fully
functional offline.

Override provenance
-------------------
The override copy always shadows the bundled copy, which is only correct while
the override is *at least as new* as the bundle. After an app-binary upgrade
(the in-place restart-swap, or a fresh reinstall/local build) the bundle can be
newer than a previously-synced override, and an unreconciled override would keep
serving stale models/distributions/feature-importances forever (offline, or
before the next online manifest sync lands). To prevent that, every successful
updater sync stamps :data:`PROVENANCE_FILE` with the asset version + build
commit it delivered, and :func:`reconcile_override_with_bundle` (run once at
startup) deletes the override model buckets whenever the running bundle is newer
than — or diverges from — that stamp, so the fresh bundled set resurfaces
immediately and the next manifest check re-delivers anything genuinely newer.
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Optional

from poe2trade import poe2trade_root
from poe2trade.app import config_manager

log = logging.getLogger(__name__)

# Stamp written by the updater into the override root after a successful sync.
PROVENANCE_FILE = "asset_provenance.json"

# Buckets that carry co-versioned model artifacts (models + their scoring,
# distribution and feature-importance sidecars). These are the buckets a stale
# override must never shadow a newer bundle for; ``files``/``base_icons`` are
# static inputs that are safe to keep.
RECONCILED_BUCKETS = ("super_models", "unsuper_models", "model_sets")
# "model_sets" is reconciled for the same reason, and it matters more: a league
# now arrives by two routes -- bundled in the app package that an in-app update
# swaps in, and synced from the manifest -- and model_set_roots searches the
# synced copy first. Without reconciliation a set downloaded against an older
# build would shadow the newer bundled one for good. Anything the manifest
# still lists is restored on the next sync.


# Set id meaning "whatever the updater syncs", i.e. the historical single-set
# behaviour. Never a directory under model_sets/.
DEFAULT_MODEL_SET = "default"


def generated_assets_root() -> Path:
    """Writable per-user root that mirrors the package ``db/`` layout."""
    return config_manager._user_config_dir() / "generated"


def provenance_path(root: Path | None = None) -> Path:
    """Path to the override provenance stamp under the generated root."""
    return (root if root is not None else generated_assets_root()) / PROVENANCE_FILE


def read_override_provenance(root: Path | None = None) -> Optional[dict]:
    """Return the override provenance stamp, or ``None`` when absent/unreadable."""
    try:
        data = json.loads(provenance_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_override_provenance(
    asset_version: str, build_commit: str | None = None, *, root: Path | None = None
) -> None:
    """Record the asset version + build commit the override was synced from.

    The stamp lives beside the synced buckets (``root`` defaults to the per-user
    generated root). Best-effort: a read-only override dir simply leaves no stamp
    (treated as legacy/stale on the next reconcile), it never breaks the app.
    """
    payload = {
        "asset_version": str(asset_version or "").strip(),
        "build_commit": str(build_commit or "").strip(),
    }
    try:
        path = provenance_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    except OSError:
        log.debug("could not write override provenance stamp", exc_info=True)


def _override_is_stale(
    provenance: Optional[dict], bundle_version: str, bundle_commit: str | None
) -> bool:
    """Decide whether the override must be cleared in favour of the bundle.

    The override is stale when there is no provenance stamp (a legacy override
    predating this mechanism — we cannot prove it is current, so the freshly
    installed bundle wins), when the bundle is a strictly newer version, or when
    the version matches but the override was delivered from a *different* known
    build commit (a same-version re-release; trust the installed bundle and let
    the next manifest sync re-deliver if needed).
    """
    # Local import avoids an import cycle (updater imports this module at load).
    from poe2trade.app.updater import is_newer_version

    if not isinstance(provenance, dict):
        return True
    prov_version = str(provenance.get("asset_version") or "").strip()
    if not prov_version:
        return True
    if is_newer_version(bundle_version, prov_version):
        return True
    if is_newer_version(prov_version, bundle_version):
        return False  # override is genuinely newer than the bundle — keep it
    # Same version: clear only when both commits are known and differ.
    prov_commit = str(provenance.get("build_commit") or "").strip().lower()
    cur_commit = str(bundle_commit or "").strip().lower()
    if prov_commit and cur_commit and prov_commit != "unknown" and cur_commit != "unknown":
        return prov_commit != cur_commit
    return False


def reconcile_override_with_bundle(
    bundle_version: str,
    *,
    build_commit: str | None = None,
    buckets: tuple[str, ...] = RECONCILED_BUCKETS,
    root: Path | None = None,
) -> list[Path]:
    """Delete override model buckets a newer/divergent bundle has superseded.

    Returns the list of override bucket dirs removed (empty when the override is
    current, absent, or genuinely newer than the bundle). Best-effort and never
    raises: a failure to remove a stale dir is logged and skipped rather than
    blocking startup.
    """
    root = root if root is not None else generated_assets_root()
    present = [root / b for b in buckets if (root / b).is_dir()]
    if not present:
        return []
    if not _override_is_stale(read_override_provenance(root), bundle_version, build_commit):
        return []

    removed: list[Path] = []
    for bucket_dir in present:
        try:
            shutil.rmtree(bucket_dir)
            removed.append(bucket_dir)
        except OSError:
            log.debug("could not remove stale override bucket %s", bucket_dir, exc_info=True)
    # The stamp described the now-deleted override; drop it so a later partial
    # sync cannot be misread as current.
    if removed:
        try:
            provenance_path(root).unlink()
        except OSError:
            pass
        log.warning(
            "asset_paths: cleared %d stale override bucket(s) superseded by bundle v%s",
            len(removed),
            bundle_version,
        )
    return removed


def bundled_db_dir(name: str) -> Path:
    """Path to the bundled ``db/<name>`` directory inside the package."""
    return Path(poe2trade_root) / "db" / name


def model_sets_root() -> Path:
    """Writable root holding alternate model sets, beside the synced assets."""
    return generated_assets_root() / "model_sets"


def model_set_roots() -> list[Path]:
    """Where model sets are looked for: synced sets first, bundled second.

    Same precedence as ``asset_search_dirs``. The bundled root matters because
    the training pipeline writes ``db/model_sets/<league>/`` in the package
    tree, so a source checkout can select the sets it just trained without
    waiting for a release to sync them into the generated root.
    """
    return [model_sets_root(), bundled_db_dir("model_sets")]


def available_model_sets(name: str = "super_models") -> list[str]:
    """Model set ids that actually have a `name` directory, sorted.

    Only sets with the requested bucket are listed: a half-populated set would
    otherwise appear selectable and then resolve to nothing. A set present in
    both roots is listed once; the synced copy wins when it is resolved.
    """
    found: set[str] = set()
    for root in model_set_roots():
        if not root.is_dir():
            continue
        try:
            entries = sorted(root.iterdir())
        except OSError:
            continue
        for entry in entries:
            try:
                bucket = entry / name
                # Retiring a league prunes its files but leaves the directory.
                # An empty bucket would still look selectable and then resolve
                # to nothing, so require it to actually hold something.
                if entry.is_dir() and bucket.is_dir() and any(bucket.iterdir()):
                    found.add(entry.name)
            except OSError:
                continue
    return sorted(found)


def model_set_dir(set_id: str, name: str = "super_models") -> Path | None:
    """The `name` directory for `set_id`, or None when it is not usable.

    Returning None rather than a missing path keeps a stale config value from
    silently emptying the search order; callers fall back to the default chain.
    """
    if not set_id or set_id == DEFAULT_MODEL_SET:
        return None
    for root in model_set_roots():
        candidate = root / set_id / name
        if candidate.is_dir():
            return candidate
    return None


MODEL_SET_METADATA_FILE = "model_set.json"


def model_set_metadata(set_id: str) -> dict:
    """Metadata a training run recorded for `set_id`, or {} when absent.

    Read from the first root that holds the set, so a synced set's own labels
    win over a local build of the same id.
    """
    if not set_id or set_id == DEFAULT_MODEL_SET:
        return {}
    for root in model_set_roots():
        path = root / set_id / MODEL_SET_METADATA_FILE
        try:
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8-sig"))
                return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            continue
    return {}


def _prettify_set_id(set_id: str) -> str:
    """Last-resort name for a set with no metadata: unslug the directory id."""
    return " ".join(part for part in set_id.replace("_", "-").split("-") if part).title()


def model_set_label(set_id: str) -> str:
    """Human name for a set: what training recorded, else the tidied id.

    A slug is not a name a player recognises, so the picker shows this.
    """
    if not set_id or set_id == DEFAULT_MODEL_SET:
        # On a build that ships its league as a set, "default" names that
        # league; calling it "Default" would hide which one is installed.
        set_id = default_equivalent_set()
        if not set_id:
            return "Default"
    meta = model_set_metadata(set_id)
    label = str(meta.get("label") or meta.get("league") or "").strip()
    return label or _prettify_set_id(set_id)


def bundled_set_league() -> str:
    """League the flat db/super_models holds, read from any pricing sidecar.

    The default entry is whatever training last mirrored, so naming it lets
    the picker show that it duplicates one of the listed leagues rather than
    looking like a separate, unrelated option.
    """
    try:
        for sidecar in sorted(bundled_db_dir("super_models").glob("*.pricing.json")):
            data = json.loads(sidecar.read_text(encoding="utf-8-sig"))
            league = str((data or {}).get("league") or "").strip()
            if league:
                return league
    except (OSError, ValueError):
        pass
    return ""


def default_equivalent_set(name: str = "super_models") -> str:
    """The set id holding the same league as the flat bundled directory.

    Training mirrors the league it just built into db/, so the default chain
    is normally a duplicate of one listed set. Callers use this to drop the
    redundant "Default" entry from the picker and preselect the real league
    instead. Returns "" when no set matches, in which case the default is a
    genuinely distinct option and must still be offered.
    """
    # The installer says which set it carries, so prefer that over inferring
    # it from the flat tree's league stamp -- which a set-shipping build has
    # no flat tree to read.
    marker = bundled_league_id()
    if marker and model_set_dir(marker, name) is not None:
        return marker
    league = bundled_set_league()
    if not league:
        return ""
    target = league.strip().casefold()
    for set_id in available_model_sets(name):
        meta = model_set_metadata(set_id)
        candidate = str(meta.get("league") or meta.get("label") or "").strip()
        if candidate.casefold() == target:
            return set_id
    return ""


# Buckets a selected league may override. Deliberately not "files" or
# "base_icons": a set carries its own models and scoring, but the shared
# lookups and icons are not league-scoped, and silently preferring an older
# set's copy of base_images.json would change unrelated behaviour.
LEAGUE_SCOPED_BUCKETS = ("super_models", "unsuper_models")


BUNDLED_SET_MARKER = "bundled_league.json"


def bundled_league_id() -> str:
    """Set id the installer carries, or "" when it ships the flat layout.

    Written at build time next to the bundled sets. It is what lets the app
    ship one league as an ordinary set at the same depth as any downloaded
    one, instead of keeping the bundled models flat and special-casing them
    forever.
    """
    marker = bundled_db_dir("model_sets") / BUNDLED_SET_MARKER
    try:
        data = json.loads(marker.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return ""
    return str((data or {}).get("id") or "").strip() if isinstance(data, dict) else ""


def active_model_set() -> str:
    """Model set id selected in config, or the default single-set behaviour."""
    try:
        raw = config_manager.load_config().get("active_model_set")
    except Exception:
        log.debug("could not read the active model set", exc_info=True)
        return DEFAULT_MODEL_SET
    set_id = str(raw or DEFAULT_MODEL_SET).strip() or DEFAULT_MODEL_SET
    if set_id != DEFAULT_MODEL_SET and model_set_dir(set_id) is not None:
        return set_id
    # Either the historical "default", or a league that is no longer installed
    # -- retired, or selected on a machine that never had it. A build that
    # ships its leagues as sets has no flat tree behind them, so resolving to
    # nothing would leave the app with no models at all rather than the wrong
    # ones. The bundled league is the one thing guaranteed present. On a flat
    # install there is no marker and this stays "default", which resolves to
    # None and leaves the previous chain untouched.
    return bundled_league_id() or DEFAULT_MODEL_SET


def selected_set_dir(name: str) -> Path | None:
    """The selected league's directory for ``name``, or None.

    None when nothing is selected, the set is gone, or the bucket is not
    league-scoped -- in every case the caller falls back to the usual chain.
    """
    if name not in LEAGUE_SCOPED_BUCKETS:
        return None
    selected = active_model_set()
    directory = model_set_dir(selected, name)
    if directory is None and selected != DEFAULT_MODEL_SET:
        supervised = model_set_dir(selected, "super_models")
        if supervised is not None:
            return supervised.parent / name
    return directory


def asset_search_dirs(name: str) -> list[Path]:
    """Search order for ``db/<name>``: league, writable override, bundled.

    The selected league goes first so every consumer follows it -- not just
    the model loaders. Scoring stats, the craft affix catalog and the feature
    importances index all resolve through here, and while this only searched
    the flat trees they stayed on one league no matter what the user picked,
    which let two readers of the same file disagree.

    A selected league replaces the model search chain. Missing models, stats,
    importances, or craft catalogs must not come from another economy.

    Use when callers resolve individual files and can fall back per file.
    """
    dirs: list[Path] = []
    chosen = selected_set_dir(name)
    if chosen is not None:
        return [chosen]
    override = generated_assets_root() / name
    if override.is_dir():
        dirs.append(override)
    dirs.append(bundled_db_dir(name))
    return dirs


def active_asset_dir(name: str) -> Path:
    """Single dir for ``db/<name>``: league, else override, else bundled.

    Use for loaders that take one base directory and cannot fall back per file.
    """
    chosen = selected_set_dir(name)
    if chosen is not None:
        return chosen
    override = generated_assets_root() / name
    return override if override.is_dir() else bundled_db_dir(name)


def resolve_asset_file(name: str, filename: str) -> Path:
    """First existing override/bundled path for ``db/<name>/<filename>``.

    Falls back to the bundled path (which may not exist) so callers can still
    branch on ``.is_file()``.
    """
    directories = asset_search_dirs(name)
    for directory in directories:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return directories[0] / filename
