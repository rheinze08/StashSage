"""Category folder and model-name conventions for the database pipeline.

Raw scraper output uses folder slugs (usually lowercase plurals), while model
artifacts use the application's established singular category names. Keep the
translation in one place so every pipeline stage reads the same folder without
renaming the corresponding model.
"""

from __future__ import annotations

from pathlib import Path

from poe2trade.db import submodule_path


# Exact raw folder names emitted by the current scraper/output collector.
RAW_CATEGORY_FOLDERS: tuple[str, ...] = (
    "body_armour",
    "Boots",
    "helmets",
    "Gloves",
    "belts",
    "amulets",
    "rings",
    "jewels",
    "quivers",
    "Tablet",
    "Waystone",
    "bows",
    "crossbows",
    "maces",
    "quarterstaves",
    "spears",
    "talismans",
    "wands",
    "sceptres",
    "staves",
    "foci",
    "shields",
)


_MODEL_NAME_BY_FOLDER_TOKEN = {
    "amulets": "Amulet",
    "belts": "Belt",
    "body_armour": "Body_Armour",
    "boots": "Boots",
    "bows": "Bow",
    "crossbows": "Crossbow",
    "foci": "Focus",
    "gloves": "Gloves",
    "helmets": "Helmet",
    "jewels": "Jewel",
    "maces": "Mace",
    "quarterstaves": "Quarterstaff",
    "quivers": "Quiver",
    "rings": "Ring",
    "sceptres": "Sceptre",
    "shields": "Shield",
    "spears": "Spear",
    "staves": "Staff",
    "tablet": "Tablet",
    "tablets": "Tablet",
    "talismans": "Talisman",
    "wands": "Wand",
    "waystone": "Waystone",
    "waystones": "Waystone",
}

_FOLDER_BY_MODEL_TOKEN = {
    model_name.lower(): folder
    for folder, model_name in _MODEL_NAME_BY_FOLDER_TOKEN.items()
    if folder not in {"tablets", "waystones"}
}


def model_category_name(category: str) -> str:
    """Return the stable model/display category for a folder or CLI token."""
    value = str(category or "").strip().replace(" ", "_")
    return _MODEL_NAME_BY_FOLDER_TOKEN.get(value.lower(), value)


def resolve_category_folder(
    category: str,
    files_root: str | Path | None = None,
) -> str:
    """Resolve a category/alias to the spelling of an existing raw folder.

    Exact or case-insensitive folder matches win. Established singular CLI
    names (for example ``Staff``) then fall back to their scraper folder slug
    (``staves``). If neither exists, the original normalized token is returned
    so callers can emit their usual missing-folder diagnostic.
    """
    root = Path(files_root) if files_root is not None else Path(submodule_path) / "files"
    requested = str(category or "").strip().replace(" ", "_")

    try:
        existing = {
            child.name.lower(): child.name
            for child in root.iterdir()
            if child.is_dir()
        }
    except OSError:
        existing = {}

    direct = existing.get(requested.lower())
    if direct is not None:
        return direct

    alias = _FOLDER_BY_MODEL_TOKEN.get(requested.lower())
    if alias is not None:
        return existing.get(alias.lower(), alias)
    return requested
