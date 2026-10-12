"""Persistent observations and serialized jobs for the desktop listing monitor."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import sqlite3
import threading
import time
from uuid import uuid4


@dataclass(frozen=True)
class WatchSpec:
    account: str
    league: str
    listing_type: str = "merchant"
    categories: tuple[str, ...] = ()
    interval_minutes: int = 30

    def __post_init__(self):
        for name in ("account", "league"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or len(value) > 128:
                raise ValueError(f"{name} is required (maximum 128 characters)")
            object.__setattr__(self, name, value.strip())
        if self.listing_type not in ("merchant", "all"):
            raise ValueError("listing_type must be merchant or all")
        if type(self.interval_minutes) is not int or not 1 <= self.interval_minutes <= 10080:
            raise ValueError("interval_minutes must be an integer from 1 to 10080")
        if not isinstance(self.categories, (tuple, list)) or any(
            not isinstance(c, str) or not c.strip() or len(c) > 128 for c in self.categories
        ) or len(self.categories) > 100:
            raise ValueError("categories must be a list of category names")
        object.__setattr__(self, "categories", tuple(sorted(set(c.strip() for c in self.categories))))

    @property
    def scope(self):
        return json.dumps([self.account.casefold(), self.league.casefold(),
                           self.listing_type, self.categories], separators=(",", ":"))


@dataclass(frozen=True)
class PollResult:
    listings: list[dict]
    complete: bool
    error: str | None = None


class PollCancelled(Exception):
    pass


class WatchConflict(ValueError):
    pass


class WatchStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS watches (
                    id TEXT PRIMARY KEY, scope TEXT UNIQUE NOT NULL, settings TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 1, enabled INTEGER NOT NULL DEFAULT 0,
                    next_check REAL, last_check REAL, last_complete INTEGER, last_error TEXT
                );
                CREATE TABLE IF NOT EXISTS listings (
                    watch_id TEXT, listing_id TEXT, data TEXT NOT NULL, visible INTEGER NOT NULL,
                    last_seen_at REAL NOT NULL, PRIMARY KEY (watch_id, listing_id)
                );
                CREATE TABLE IF NOT EXISTS watch_revisions (
                    watch_id TEXT, revision INTEGER, settings TEXT NOT NULL,
                    PRIMARY KEY (watch_id, revision)
                );
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY, watch_id TEXT, revision INTEGER,
                    observed_at REAL, data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, watch_id TEXT, revision INTEGER, type TEXT,
                    listing_id TEXT, observed_at REAL, last_seen_at REAL,
                    before_data TEXT, after_data TEXT
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, watch_id TEXT, status TEXT,
                    started_at REAL, finished_at REAL, error TEXT, count INTEGER
                );
                CREATE INDEX IF NOT EXISTS event_watch ON events(watch_id, id);
                CREATE INDEX IF NOT EXISTS observation_watch ON observations(watch_id, id);
                CREATE INDEX IF NOT EXISTS run_watch ON runs(watch_id, started_at);
                CREATE TABLE IF NOT EXISTS watch_requests (
                    watch_id TEXT, request_id TEXT, run_id TEXT NOT NULL,
                    PRIMARY KEY (watch_id, request_id)
                );
                CREATE TABLE IF NOT EXISTS watch_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            watch_columns = {r[1] for r in db.execute("PRAGMA table_info(watches)")}
            for name, declaration in {"settings_version": "INTEGER NOT NULL DEFAULT 1",
                                      "baseline_ready": "INTEGER NOT NULL DEFAULT 0",
                                      "last_complete_at": "REAL"}.items():
                if name not in watch_columns:
                    db.execute(f"ALTER TABLE watches ADD COLUMN {name} {declaration}")
            if "baseline" not in {r[1] for r in db.execute("PRAGMA table_info(events)")}:
                db.execute("ALTER TABLE events ADD COLUMN baseline INTEGER NOT NULL DEFAULT 0")
            db.execute("INSERT OR IGNORE INTO watch_metadata VALUES('history_generation',?)", (uuid4().hex,))
            db.execute("INSERT OR IGNORE INTO watch_revisions SELECT id,revision,settings FROM watches")

    @contextmanager
    def _db(self):
        with self._lock:
            db = sqlite3.connect(self.path, timeout=10)
            db.row_factory = sqlite3.Row
            try:
                with db:
                    yield db
            finally:
                db.close()

    @staticmethod
    def _watch(db, watch_id):
        row = db.execute("SELECT * FROM watches WHERE id=?", (watch_id,)).fetchone()
        if row is None:
            raise KeyError("Watch not found")
        result = dict(row)
        result.pop("scope")
        result["settings"] = json.loads(result["settings"])
        result["enabled"] = bool(result["enabled"])
        result["baseline_ready"] = bool(result["baseline_ready"])
        if result["last_complete"] is not None:
            result["last_complete"] = bool(result["last_complete"])
        latest = db.execute("SELECT * FROM runs WHERE watch_id=? ORDER BY started_at DESC, rowid DESC LIMIT 1",
                            (watch_id,)).fetchone()
        result["last_run"] = dict(latest) if latest else None
        return result

    def get(self, watch_id):
        with self._db() as db:
            return self._watch(db, watch_id)

    def watches(self):
        with self._db() as db:
            return [self._watch(db, r[0]) for r in db.execute("SELECT id FROM watches ORDER BY rowid")]

    def save(self, spec: WatchSpec, *, watch_id=None, expected_version=None):
        data = json.dumps(asdict(spec), ensure_ascii=False)
        with self._db() as db:
            if watch_id is None:
                found = db.execute("SELECT id FROM watches WHERE scope=?", (spec.scope,)).fetchone()
                watch_id = found[0] if found else uuid4().hex
            previous = db.execute("SELECT * FROM watches WHERE id=?", (watch_id,)).fetchone()
            if expected_version is not None and (previous is None or previous["settings_version"] != expected_version):
                raise WatchConflict("Watch settings changed; refresh before editing")
            changed = previous is not None and previous["scope"] != spec.scope
            try:
                if previous:
                    db.execute("UPDATE watches SET scope=?, settings=?, revision=revision+?, settings_version=settings_version+1 WHERE id=?",
                               (spec.scope, data, int(changed), watch_id))
                    if changed:
                        db.execute("DELETE FROM listings WHERE watch_id=?", (watch_id,))
                        db.execute("UPDATE watches SET last_check=NULL,last_complete=NULL,last_error=NULL,last_complete_at=NULL,baseline_ready=0 WHERE id=?", (watch_id,))
                else:
                    db.execute("INSERT INTO watches(id,scope,settings) VALUES(?,?,?)", (watch_id, spec.scope, data))
                db.execute("INSERT OR IGNORE INTO watch_revisions SELECT id,revision,settings FROM watches WHERE id=?", (watch_id,))
            except sqlite3.IntegrityError as exc:
                raise ValueError("A watch for these settings already exists") from exc
            return self._watch(db, watch_id)

    def set_enabled(self, watch_id, enabled, now):
        with self._db() as db:
            self._watch(db, watch_id)
            db.execute("UPDATE watches SET enabled=?, next_check=? WHERE id=?",
                       (int(enabled), now if enabled else None, watch_id))
            return self._watch(db, watch_id)

    def record(self, watch_id, result: PollResult, observed_at):
        # Validate before opening a transaction so malformed/duplicated fetches
        # cannot turn into a partially committed baseline.
        rows = {}
        for row in result.listings:
            key = row.get("listing_id")
            price = row.get("price")
            if not isinstance(key, str) or not key or key in rows:
                raise ValueError("Listings must have unique, nonempty listing_id values")
            if price is not None and (type(price) not in (int, float) or not math.isfinite(price) or price < 0):
                raise ValueError("Listing price must be a nonnegative finite number or null")
            rows[key] = dict(row)
        with self._db() as db:
            watch = self._watch(db, watch_id)
            before = {r["listing_id"]: dict(r) for r in db.execute("SELECT * FROM listings WHERE watch_id=?", (watch_id,))}

            def event(kind, key, old, new, last_seen):
                db.execute("INSERT INTO events(watch_id,revision,type,listing_id,observed_at,last_seen_at,before_data,after_data,baseline) VALUES(?,?,?,?,?,?,?,?,?)",
                           (watch_id, watch["revision"], kind, key, observed_at, last_seen,
                            json.dumps(old, ensure_ascii=False) if old is not None else None,
                            json.dumps(new, ensure_ascii=False) if new is not None else None, int(not watch["baseline_ready"])))

            for key, row in rows.items():
                previous = before.get(key)
                old = json.loads(previous["data"]) if previous else None
                if previous is None:
                    event("listing_added", key, None, row, None)
                elif not previous["visible"]:
                    event("listing_reappeared", key, old, row, previous["last_seen_at"])
                elif (old.get("price"), old.get("currency")) != (row.get("price"), row.get("currency")):
                    event("price_changed", key, old, row, previous["last_seen_at"])
                data = json.dumps(row, ensure_ascii=False)
                db.execute("INSERT OR REPLACE INTO listings VALUES(?,?,?,?,?)", (watch_id, key, data, 1, observed_at))
                db.execute("INSERT INTO observations(watch_id,revision,observed_at,data) VALUES(?,?,?,?)",
                           (watch_id, watch["revision"], observed_at, data))
            if result.complete:
                for key, previous in before.items():
                    if previous["visible"] and key not in rows:
                        event("listing_no_longer_observed", key, json.loads(previous["data"]), None, previous["last_seen_at"])
                        db.execute("UPDATE listings SET visible=0 WHERE watch_id=? AND listing_id=?", (watch_id, key))
            db.execute("UPDATE watches SET last_check=?,last_complete=?,last_error=? WHERE id=?",
                       (observed_at, int(result.complete), result.error, watch_id))
            if result.complete:
                db.execute("UPDATE watches SET baseline_ready=1,last_complete_at=? WHERE id=?", (observed_at, watch_id))

    def listings(self, watch_id):
        with self._db() as db:
            self._watch(db, watch_id)
            return [json.loads(r["data"]) | {"last_seen_at": r["last_seen_at"]}
                    for r in db.execute("SELECT * FROM listings WHERE watch_id=? AND visible=1 ORDER BY listing_id", (watch_id,))]

    def observations(self, watch_id):
        with self._db() as db:
            self._watch(db, watch_id)
            return [json.loads(r["data"]) | {"observed_at": r["observed_at"], "revision": r["revision"],
                                            "settings": json.loads(r["settings"])}
                    for r in db.execute("SELECT o.*, r.settings FROM observations o JOIN watch_revisions r USING(watch_id,revision) WHERE watch_id=? ORDER BY o.id", (watch_id,))]

    def events(self, watch_id, *, after=0, limit=500):
        with self._db() as db:
            self._watch(db, watch_id)
            out = []
            for r in db.execute("SELECT e.*,r.settings FROM events e JOIN watch_revisions r USING(watch_id,revision) WHERE watch_id=? AND e.id>? ORDER BY e.id LIMIT ?", (watch_id, after, limit)):
                row = dict(r)
                before, following = row.pop("before_data"), row.pop("after_data")
                row["before"] = json.loads(before) if before else None
                row["after"] = json.loads(following) if following else None
                row["settings"] = json.loads(row["settings"])
                row["baseline"] = bool(row["baseline"])
                out.append(row)
            return out

    def history_identity(self, watch_id):
        with self._db() as db:
            self._watch(db, watch_id)
            generation = db.execute("SELECT value FROM watch_metadata WHERE key='history_generation'").fetchone()[0]
            head = db.execute("SELECT COALESCE(MAX(id),0) FROM events WHERE watch_id=?", (watch_id,)).fetchone()[0]
            return {"generation": generation, "head_cursor": head}

    def requested_run(self, watch_id, request_id):
        with self._db() as db:
            row = db.execute("SELECT run_id FROM watch_requests WHERE watch_id=? AND request_id=?",
                             (watch_id, request_id)).fetchone()
            return self.run(row[0]) if row else None

    def remember_request(self, watch_id, request_id, run_id):
        with self._db() as db:
            db.execute("INSERT OR IGNORE INTO watch_requests VALUES(?,?,?)", (watch_id, request_id, run_id))

    def begin_run(self, watch_id, now, request_id=None):
        with self._db() as db:
            self._watch(db, watch_id)
            run_id = uuid4().hex
            db.execute("INSERT INTO runs(id,watch_id,status,started_at) VALUES(?,?,'running',?)", (run_id, watch_id, now))
            if request_id:
                db.execute("INSERT INTO watch_requests VALUES(?,?,?)", (watch_id, request_id, run_id))
        return self.run(run_id)

    def run(self, run_id):
        with self._db() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                raise KeyError("Run not found")
            return dict(row)

    def finish_run(self, run_id, now, status, *, error=None, count=0):
        with self._db() as db:
            run = self.run(run_id)
            watch = self._watch(db, run["watch_id"])
            db.execute("UPDATE runs SET status=?,finished_at=?,error=?,count=? WHERE id=?", (status, now, error, count, run_id))
            next_check = now + watch["settings"]["interval_minutes"] * 60 if watch["enabled"] else None
            db.execute("UPDATE watches SET next_check=? WHERE id=?", (next_check, watch["id"]))
            if status in ("failed", "interrupted"):
                db.execute("UPDATE watches SET last_complete=0,last_error=? WHERE id=?", (error, watch["id"]))

    def recover(self, now):
        with self._db() as db:
            ids = [r[0] for r in db.execute("SELECT id FROM runs WHERE status='running'")]
        for run_id in ids:
            self.finish_run(run_id, now, "interrupted", error="App stopped during the previous check")
        if ids:
            with self._db() as db:
                db.execute("UPDATE watches SET next_check=? WHERE enabled=1", (now,))


class WatchManager:
    def __init__(self, store: WatchStore, collector, *, clock=time.time):
        self.store, self.collector, self.clock = store, collector, clock
        self._lock = threading.RLock()
        self._worker = None
        self._active = None
        self._cancel = threading.Event()
        self._shutdown = threading.Event()
        self._scheduler = None
        self.store.recover(self.clock())

    def save(self, spec, *, watch_id=None, expected_version=None):
        with self._lock:
            if self._active and (watch_id is None or self._active["watch_id"] == watch_id):
                raise ValueError("A check is running; pause it before changing settings")
            if watch_id is not None:
                self.store.get(watch_id)
            return self.store.save(spec, watch_id=watch_id, expected_version=expected_version)

    def start(self, watch_id):
        with self._lock:
            return self.store.set_enabled(watch_id, True, self.clock())

    def pause(self, watch_id):
        with self._lock:
            watch = self.store.set_enabled(watch_id, False, self.clock())
            if self._active and self._active["watch_id"] == watch_id:
                self._cancel.set()
            return watch

    def check_now(self, watch_id, request_id=None):
        with self._lock:
            if request_id is not None:
                if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 128:
                    raise ValueError("X-Request-ID must contain 1 to 128 characters")
                previous = self.store.requested_run(watch_id, request_id)
                if previous:
                    return previous
            if self._shutdown.is_set():
                raise ValueError("StashWatch is stopping")
            watch = self.store.get(watch_id)
            if self._active:
                if self._active["watch_id"] == watch_id:
                    if request_id:
                        self.store.remember_request(watch_id, request_id, self._active["id"])
                    return self.store.run(self._active["id"])
                raise ValueError("Another check is running; try again when it finishes")
            run = self.store.begin_run(watch_id, self.clock(), request_id=request_id)
            self._active = run
            self._cancel = threading.Event()
            self._worker = threading.Thread(target=self._poll, args=(run, WatchSpec(**watch["settings"]), self._cancel),
                                            name="StashWatch poll", daemon=True)
            self._worker.start()
            return run

    def _poll(self, run, spec, cancel):
        try:
            result = self.collector(spec, cancel)
            with self._lock:
                if cancel.is_set():
                    raise PollCancelled()
                self.store.record(run["watch_id"], result, self.clock())
                self.store.finish_run(run["id"], self.clock(), "complete" if result.complete else "incomplete",
                                      error=result.error, count=len(result.listings))
        except PollCancelled:
            self.store.finish_run(run["id"], self.clock(), "cancelled")
        except Exception as exc:
            self.store.finish_run(run["id"], self.clock(), "failed", error=str(exc))
        finally:
            with self._lock:
                self._active = None

    def tick(self):
        with self._lock:
            if self._active or self._shutdown.is_set():
                return None
            due = [w for w in self.store.watches() if w["enabled"] and
                   (w["next_check"] is None or w["next_check"] <= self.clock())]
            if due:
                return self.check_now(min(due, key=lambda w: w["next_check"] or 0)["id"])
            return None

    def run_scheduler(self):
        if self._scheduler is not None:
            return

        def loop():
            while not self._shutdown.wait(1):
                self.tick()

        self._scheduler = threading.Thread(target=loop, name="StashWatch timer", daemon=True)
        self._scheduler.start()

    def wait_idle(self, timeout=35):
        worker = self._worker
        if worker:
            worker.join(timeout)
        return worker is None or not worker.is_alive()

    def close(self):
        with self._lock:
            self._shutdown.set()
            self._cancel.set()
        if self._scheduler:
            self._scheduler.join(2)
        return self.wait_idle()
