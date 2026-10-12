"""Account-scoped listing observations, without the file-based ML pipeline."""
from __future__ import annotations

from functools import lru_cache
import math
import time
from urllib.parse import quote

import requests

from poe2trade.app.stash_watch import PollCancelled, PollResult


@lru_cache(maxsize=1)
def selections():
    from poe2trade.utils.scrape_stash_utils import STASH_SCRAPE_SELECTIONS
    return {row["name"]: row for row in STASH_SCRAPE_SELECTIONS}


def catalog():
    from poe2trade.app import asset_paths
    leagues = []
    for set_id in asset_paths.available_model_sets():
        meta = asset_paths.model_set_metadata(set_id)
        league = str(meta.get("league") or meta.get("label") or "").strip()
        if league and league not in leagues:
            leagues.append(league)
    return {"categories": list(selections()), "leagues": leagues}


def _wait(seconds, stop):
    if stop.wait(seconds):
        raise PollCancelled()


class TradeCollector:
    def __init__(self, *, session=None, minimum_delay=1.0, wait=_wait, clock=time.monotonic):
        self.session = session if session is not None else requests.Session()
        self.session.headers.update({"User-Agent": "StashSage-StashWatch/1.0", "Accept": "application/json"})
        self.minimum_delay, self.wait, self.clock = minimum_delay, wait, clock
        self._next_request = 0.0

    def _headers_delay(self, headers):
        # The API describes its live quota in response headers. Waiting a whole
        # window near exhaustion is conservative because it supplies no hit times.
        headers = {key.lower(): value for key, value in headers.items()}
        delay = 0.0
        for method in headers.get("x-rate-limit-rules", "").split(","):
            method = method.strip().lower()
            rules = headers.get(f"x-rate-limit-{method}", "").split(",")
            states = headers.get(f"x-rate-limit-{method}-state", "").split(",")
            for rule, state in zip(rules, states):
                try:
                    limit, window, _ = (int(part) for part in rule.split(":"))
                    hits, _, timeout = (int(part) for part in state.split(":"))
                except (ValueError, TypeError):
                    continue
                delay = max(delay, timeout, window if hits >= limit - 1 else 0)
        return delay

    def _request(self, method, url, stop, **kwargs):
        for attempt in range(3):
            if stop.is_set():
                raise PollCancelled()
            delay = max(0, self._next_request - self.clock())
            if delay:
                self.wait(delay, stop)
            if stop.is_set():
                raise PollCancelled()
            response = self.session.request(method, url, timeout=30, **kwargs)
            quota_delay = self._headers_delay(response.headers)
            self._next_request = self.clock() + max(self.minimum_delay, quota_delay)
            if response.status_code == 429:
                try:
                    retry = float(response.headers.get("Retry-After", "60"))
                    if not math.isfinite(retry):
                        retry = 60
                except (TypeError, ValueError):
                    retry = 60
                self._next_request = max(self._next_request, self.clock() + max(1, retry))
                if attempt < 2:
                    continue
            if response.status_code != 200:
                raise ValueError(f"Trade API returned HTTP {response.status_code}")
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError("Trade API returned an invalid response")
            return body
        raise ValueError("Trade API rate limit did not clear")

    @staticmethod
    def _query(spec, selection):
        filters = {"trade_filters": {"filters": {"account": {"input": spec.account},
                                                   "sale_type": {"option": "any"}}}}
        query = {"status": {"option": "securable" if spec.listing_type == "merchant" else "available"},
                 "stats": [{"type": "and", "filters": []}], "filters": filters}
        if selection and selection.get("category_option"):
            filters["type_filters"] = {"filters": {"category": {"option": selection["category_option"]}}}
        if selection and selection.get("type_option"):
            query["type"] = selection["type_option"]
        return {"query": query, "sort": {"price": "asc"}}

    @staticmethod
    def _listing(entry, category):
        key = entry.get("id")
        if not isinstance(key, str) or not key:
            raise ValueError("Fetched listing has no ID")
        item = entry.get("item") or {}
        listing = entry.get("listing") or {}
        price = listing.get("price") or {}
        stash = listing.get("stash") or {}
        return {"listing_id": key, "item_id": item.get("id"),
                "item": " — ".join(filter(None, [item.get("name"), item.get("typeLine") or item.get("baseType")])),
                "category": category, "price": price.get("amount"), "currency": price.get("currency", ""),
                "stash_name": stash.get("name", ""), "stash_x": stash.get("x"), "stash_y": stash.get("y")}

    def __call__(self, spec, stop):
        selected = [(name, selections()[name]) for name in spec.categories] if spec.categories else [("All listings", None)]
        rows, errors = {}, []
        for name, selection in selected:
            try:
                search = self._request("POST", f"https://www.pathofexile.com/api/trade2/search/poe2/{quote(spec.league, safe='')}",
                                       stop, json=self._query(spec, selection))
                ids, total = search.get("result"), search.get("total")
                if not isinstance(ids, list) or any(not isinstance(key, str) or not key for key in ids) or \
                        type(total) is not int or total < len(ids) or len(set(ids)) != len(ids):
                    raise ValueError("Invalid search coverage")
                if len(ids) < total:
                    errors.append(f"{name}: search capped ({len(ids)} of {total} listings)")
                if ids and not isinstance(search.get("id"), str):
                    raise ValueError("Missing search ID")
                fetched = set()
                for offset in range(0, len(ids), 10):
                    chunk = ids[offset:offset + 10]
                    body = self._request("GET", f"https://www.pathofexile.com/api/trade2/fetch/{','.join(quote(key, safe='') for key in chunk)}",
                                         stop, params={"query": search["id"]})
                    entries = body.get("result")
                    if not isinstance(entries, list):
                        raise ValueError("Invalid fetch response")
                    for entry in entries:
                        if entry is None:
                            continue
                        row = self._listing(entry, name)
                        key = row["listing_id"]
                        if key not in chunk or key in fetched:
                            raise ValueError("Unexpected or duplicate fetched listing ID")
                        fetched.add(key)
                        rows[key] = row
                if len(fetched) != len(ids):
                    errors.append(f"{name}: only fetched {len(fetched)} of {len(ids)} returned IDs")
            except PollCancelled:
                raise
            except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
                errors.append(f"{name}: {exc}")
        return PollResult(list(rows.values()), not errors, "; ".join(errors) or None)

    def close(self):
        self.session.close()
