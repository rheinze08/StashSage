"""Small runtime-only poe2scout currency-rate client.

This module is intentionally independent of the scraper package. The desktop
app needs live conversion rates, but it does not need scraper planning,
fetching, or generated scrape output.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests


RATES_URL = os.getenv("SCRAPER_RATES_URL", "https://poe2scout.com/api/poe2/Leagues")
RATES_TTL = float(os.getenv("SCRAPER_RATES_TTL_HOURS", "6")) * 3600
FALLBACK = {"exalted": 1.0, "chaos": 62.9, "divine": 499.55}


def configured_league(cache_path: str | os.PathLike[str] | None = None) -> str:
    """Resolve the app's current league without importing scraper config."""
    configured = os.getenv("POE_LEAGUE", "").strip()
    if configured:
        return configured
    if cache_path:
        try:
            with open(cache_path, "r", encoding="utf-8") as handle:
                cached = json.load(handle)
            league = str(cached.get("league") or "").strip()
            if league:
                return league
        except (OSError, TypeError, json.JSONDecodeError):
            pass
    return "Standard"


def _derive(league: dict) -> dict[str, float]:
    divine_ex = float(league["DivinePrice"])
    divine_chaos = float(league["ChaosDivinePrice"])
    chaos_ex = divine_ex / divine_chaos if divine_chaos else FALLBACK["chaos"]
    return {"exalted": 1.0, "chaos": chaos_ex, "divine": divine_ex}


def get_rates(league_name: str, cache_path: str | os.PathLike[str] | None = None,
              timeout: float = 10, log=print) -> dict:
    """Return exalted-equivalent rates, using live data, cache, then fallback."""
    try:
        response = requests.get(RATES_URL, timeout=timeout)
        response.raise_for_status()
        leagues = response.json()
        match = next(
            (item for item in leagues if item.get("Value") == league_name and item.get("IsCurrent")),
            None,
        ) or next((item for item in leagues if item.get("Value") == league_name), None)
        if match is None:
            raise ValueError(f"league {league_name!r} not found in poe2scout response")
        rates = _derive(match)
        rates.update(league=league_name, source="poe2scout", fetched_at=time.time())
        if cache_path:
            _write_cache(cache_path, rates)
        return rates
    except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as exc:
        log(f"[Rates] live fetch failed ({exc}); trying cache/fallback.")

    if cache_path and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as handle:
                cached = json.load(handle)
            if time.time() - cached.get("fetched_at", 0) < RATES_TTL:
                cached["source"] = "cache"
                return cached
        except (OSError, TypeError, json.JSONDecodeError):
            pass

    result = dict(FALLBACK)
    result.update(league=league_name, source="fallback")
    return result


def _write_cache(path: str | os.PathLike[str], rates: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.tmp")
    temporary.write_text(json.dumps(rates), encoding="utf-8")
    temporary.replace(target)
