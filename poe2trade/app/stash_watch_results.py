"""Desktop projections and exports; asking prices stay in their recorded currency."""
from __future__ import annotations

import csv
import io
import json


STATUS_FILTERS = {"All": (), "Still listed": ("Yes",), "No longer observed": ("No",),
                  "Unknown": ("Unknown",)}
CHANGE_LABELS = {"listing_added": "New", "price_changed": "Price changed",
                 "listing_no_longer_observed": "No longer observed", "listing_reappeared": "Appeared again"}
COUNT_KEYS = {"listing_added": "new", "price_changed": "price_changed",
              "listing_no_longer_observed": "no_longer_observed", "listing_reappeared": "reappeared"}


def category_label(value):
    aliases = {"Mace_One_Hand_Mace": "One-Handed Mace", "Mace_Two_Hand_Mace": "Two-Handed Mace"}
    return aliases.get(value, str(value).replace("_", " "))


def price_text(amount, currency):
    if amount is None:
        return "Unpriced"
    labels = {"exalted": "exalts", "divine": "divines", "chaos": "chaos"}
    return f"{amount:g} {labels.get(currency, currency)}".strip()


def previous_price_text(row):
    return price_text(row.get("previous_price"), row.get("previous_currency", "")) if row.get("had_previous") else "—"


def snapshot_rows(before, rows, *, baseline, complete, observed_at):
    out = []
    for key in sorted(before.keys() | rows.keys()):
        previous = before.get(key)
        old = json.loads(previous["data"]) if previous else None
        current = rows.get(key)
        if current is not None:
            change = "Baseline" if baseline else "New" if old is None else "Appeared again" if not previous["visible"] else (
                "Price changed" if (old.get("price"), old.get("currency")) != (current.get("price"), current.get("currency")) else "Unchanged")
            row = dict(current)
            row.update(remaining="Yes", last_seen_at=observed_at, absent_at=None,
                       first_seen_at=previous.get("first_seen_at") if previous else observed_at)
        else:
            row = dict(old)
            change = "No longer observed" if complete and previous["visible"] else "Unchanged" if complete else "Unknown"
            row.update(remaining="No" if complete else "Unknown", last_seen_at=previous["last_seen_at"],
                       first_seen_at=previous.get("first_seen_at"),
                       absent_at=observed_at if complete and previous["visible"] else previous.get("absent_at"))
        row.update(change=change, had_previous=old is not None,
                   previous_price=old.get("price") if old else None,
                   previous_currency=old.get("currency", "") if old else "")
        out.append(row)
    return out


def result_csv(result):
    columns = ("listing_id", "item", "remaining", "previous_price", "previous_currency", "price", "currency",
               "change", "stash_name", "last_seen_at", "check_id", "check_time", "coverage",
               "account", "league", "listing_type", "categories", "revision")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    run = result.get("run") or {}
    scope = result["scope"]
    for row in result["rows"]:
        writer.writerow(row | {"check_id": run.get("id", ""), "check_time": run.get("observed_at", ""),
                               "coverage": run.get("status", "last-known legacy records"),
                               "account": scope["account"], "league": scope["league"], "listing_type": scope["listing_type"],
                               "categories": json.dumps(scope["categories"]), "revision": run.get("revision", "")})
    return "\ufeff" + stream.getvalue()
