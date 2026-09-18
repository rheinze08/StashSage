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


RATES_URL = os.getenv("SCRAPER_RATES_URL", "https://api.poe2scout.com/poe2/Leagues")
# Secondary source, mirroring the scraper's client. poe2scout's Leagues path
# now answers 200 with the site's HTML shell instead of JSON, so the primary
# fails on every call; without this tier the app silently priced against
# FALLBACK, which is roughly 2x off the live divine rate.
NINJA_URL = os.getenv(
    "SCRAPER_NINJA_RATES_URL",
    "https://poe.ninja/poe2/api/economy/exchange/current/overview",
)
RATES_TTL = float(os.getenv("SCRAPER_RATES_TTL_HOURS", "6")) * 3600
FALLBACK = {"exalted": 1.0, "chaos": 62.9, "divine": 499.55}


def _json_or_raise(response, source: str):
    """Parse JSON, rejecting a success status that carries an HTML body.

    A misrouted API path can answer 200 with a SPA shell, which
    ``raise_for_status`` happily accepts and ``response.json()`` then reports as
    "Expecting value: line 1 column 1 (char 0)" -- indistinguishable from an
    outage in the log, which is how this went unnoticed. Naming it makes the
    cause obvious the next time an endpoint moves.
    """
    content_type = str(response.headers.get("Content-Type", "")).lower()
    if "json" not in content_type:
        raise ValueError(
            f"{source} returned {content_type or 'an unknown content type'} "
            f"rather than JSON (HTTP {response.status_code}); the endpoint has "
            "probably moved"
        )
    return response.json()


def _from_ninja(league_name: str, timeout: float) -> dict[str, float]:
    """exalted-equivalents from poe.ninja's poe2 exchange overview.

    ``core.rates`` maps a unit to how many of it one ``primary`` buys, so with
    primary=divine, chaos in exalted is ``divine_ex / chaos_per_divine`` rather
    than a direct lookup. ``primary`` is asserted rather than assumed: if
    poe.ninja ever re-bases to exalted the arithmetic silently inverts.
    """
    response = requests.get(
        NINJA_URL,
        params={"league": league_name, "type": "Currency"},
        timeout=timeout,
    )
    response.raise_for_status()
    core = _json_or_raise(response, "poe.ninja")["core"]
    primary = core.get("primary")
    if primary != "divine":
        raise ValueError(f"poe.ninja primary is {primary!r}, expected 'divine'")
    rates = core["rates"]
    divine_ex = float(rates["exalted"])
    chaos_per_divine = float(rates["chaos"])
    if divine_ex <= 0 or chaos_per_divine <= 0:
        raise ValueError(f"poe.ninja returned non-positive rates: {rates}")
    return {"exalted": 1.0, "chaos": divine_ex / chaos_per_divine, "divine": divine_ex}


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
        leagues = _json_or_raise(response, "poe2scout")
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
        log(f"[Rates] poe2scout fetch failed ({exc}); trying poe.ninja.")

    try:
        rates = _from_ninja(league_name, timeout)
        rates.update(league=league_name, source="poe.ninja", fetched_at=time.time())
        if cache_path:
            _write_cache(cache_path, rates)
        return rates
    except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as exc:
        log(f"[Rates] poe.ninja fetch failed ({exc}); trying cache/fallback.")

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
