"""Shared runtime currency conversions backed by poe2scout's league rates.

The properties on :data:`conversion` are always in-memory reads.  Network I/O
only happens through :meth:`CurrencyConversions.refresh`, which callers should
run outside the GUI thread.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from poe2trade import poe2trade_root
from poe2trade.app import config_manager
from poe2trade import runtime_rates as scout_rates

_LOG = logging.getLogger(__name__)
# The frozen bundle is read-only. Runtime rates therefore belong under the
# per-user StashSage directory; the bundled data remains an initial fallback.
_BUNDLED_RATES_DIR = Path(poe2trade_root) / "data"
_RATES_DIR = config_manager._user_config_dir() / "data"
_RUNTIME_RATES_PATH = _RATES_DIR / "rates.json"
_CACHE_PATH = _RATES_DIR / ".live_rates_cache.json"
_BUNDLED_RUNTIME_RATES_PATH = _BUNDLED_RATES_DIR / "rates.json"
TRAINING_SNAPSHOT_PATH = _RATES_DIR / "training_conversion_snapshot.json"
TRAINING_INDEX_PATH = Path(poe2trade_root) / "db" / "files" / "training_conversion_index.json"
TRAINING_INDEX_MOCK_PATH = Path(poe2trade_root) / "db" / "files" / "training_conversion_index.mock.json"
_FALLBACK = {"exalted": 1.0, "chaos": 61.0, "divine": 449.0, "annul": 361.0}


@dataclass(frozen=True)
class RateSnapshot:
    exalted: float
    chaos: float
    divine: float
    annul: float
    league: str = ""
    source: str = "bundled"
    fetched_at: float | None = None

    def as_dict(self) -> dict[str, float | str | None]:
        return {
            "exalted": self.exalted,
            "chaos": self.chaos,
            "divine": self.divine,
            "annul": self.annul,
            "league": self.league,
            "source": self.source,
            "fetched_at": self.fetched_at,
        }


class CurrencyConversions:
    """Thread-safe current conversion snapshot and controlled refresh API."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._snapshot = self._load_runtime_snapshot()

    @property
    def exalted(self) -> float:
        return self.snapshot().exalted

    @property
    def chaos(self) -> float:
        return self.snapshot().chaos

    @property
    def divine(self) -> float:
        return self.snapshot().divine

    @property
    def annul(self) -> float:
        return self.snapshot().annul

    def snapshot(self) -> RateSnapshot:
        with self._lock:
            return self._snapshot

    def quote(self, currency: str) -> float:
        key = self._normalize(currency)
        return float(getattr(self.snapshot(), key))

    def convert(self, amount: float, source: str, target: str = "exalted") -> float:
        """Convert an amount through exalted equivalents using the current snapshot."""
        snapshot = self.snapshot()
        source_rate = float(getattr(snapshot, self._normalize(source)))
        target_rate = float(getattr(snapshot, self._normalize(target)))
        return float(amount) * source_rate / target_rate

    def refresh(self, *, force: bool = False, timeout: float = 10.0) -> RateSnapshot:
        """Refresh from poe2scout, or use the fresh shared cache when allowed."""
        cached = None if force else self._read_fresh_cache()
        if cached is None:
            league = scout_rates.configured_league(_CACHE_PATH)
            if league == "Standard" and not os.environ.get("POE_LEAGUE"):
                try:
                    with _BUNDLED_RUNTIME_RATES_PATH.open("r", encoding="utf-8") as handle:
                        league = str(json.load(handle).get("league") or league)
                except (OSError, TypeError, ValueError, json.JSONDecodeError):
                    pass
            payload = scout_rates.get_rates(
                league,
                cache_path=str(_CACHE_PATH),
                timeout=timeout,
                log=_LOG.warning,
            )
            if payload.get("source") == "fallback":
                try:
                    with _BUNDLED_RUNTIME_RATES_PATH.open("r", encoding="utf-8") as handle:
                        bundled = json.load(handle)
                    if isinstance(bundled, dict):
                        payload = dict(bundled)
                        payload["source"] = "bundled"
                except (OSError, TypeError, ValueError, json.JSONDecodeError):
                    pass
        else:
            payload = cached
        snapshot = self._snapshot_from_payload(payload)
        with self._lock:
            self._snapshot = snapshot
        if snapshot.source != "fallback":
            self._write_runtime_rates(snapshot)
        return snapshot

    def write_training_snapshot(self, *, context: Mapping[str, object] | None = None) -> Path:
        """Persist the exact conversion state used by a successful training run.

        This is intentionally separate from ``rates.json``: live rates may be
        refreshed later, while this file remains the historical price context
        for the model artifacts that were just produced.
        """
        payload = self.build_training_snapshot(context=context)
        _RATES_DIR.mkdir(parents=True, exist_ok=True)
        temp = TRAINING_SNAPSHOT_PATH.with_suffix(".json.tmp")
        try:
            temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            temp.replace(TRAINING_SNAPSHOT_PATH)
        except OSError:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        return TRAINING_SNAPSHOT_PATH

    def build_training_snapshot(
        self, *, context: Mapping[str, object] | None = None
    ) -> dict[str, object]:
        """Capture the current rates once for a model artifact or training run."""
        return {
            "schema_version": 1,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "conversions": self.snapshot().as_dict(),
            "context": dict(context or {}),
        }

    def write_model_snapshot(
        self,
        model_path: str | Path,
        snapshot: Mapping[str, object],
    ) -> Path:
        """Write an immutable, human-readable snapshot beside one model pickle."""
        artifact = Path(model_path)
        sidecar_path = artifact.with_suffix(".training.json")
        payload = dict(snapshot)
        payload["model_artifact"] = artifact.name
        temp = sidecar_path.with_suffix(".json.tmp")
        try:
            temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            temp.replace(sidecar_path)
        except OSError:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        self.rebuild_training_conversion_index()
        return sidecar_path

    def rebuild_training_conversion_index(self) -> Path:
        """Combine model sidecars into the one-file lookup used by prediction UI."""
        models: dict[str, object] = {}
        for bucket in ("super_models", "unsuper_models"):
            model_dir = Path(poe2trade_root) / "db" / bucket
            if not model_dir.is_dir():
                continue
            for sidecar_path in sorted(model_dir.glob("*.training.json")):
                try:
                    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    _LOG.warning("Ignoring unreadable model conversion snapshot: %s", sidecar_path)
                    continue
                if not isinstance(payload, dict):
                    continue
                artifact = str(payload.get("model_artifact") or "").strip()
                if artifact:
                    models[f"{bucket}/{artifact}"] = payload
        payload = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "models": models,
        }
        _RATES_DIR.mkdir(parents=True, exist_ok=True)
        temp = TRAINING_INDEX_PATH.with_suffix(".json.tmp")
        try:
            temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            temp.replace(TRAINING_INDEX_PATH)
        except OSError:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        return TRAINING_INDEX_PATH

    @staticmethod
    def load_training_conversion_index() -> Mapping[str, object] | None:
        """Load the consolidated model-rate lookup once in the prediction worker.

        The bundled mock is only a visual-development fallback.  A real index
        created by training always takes priority, including when the
        application is running from a frozen bundle with a separate writable
        runtime location. The serve package intentionally has no desktop
        ``asset_paths`` module, so that optional override lookup must not prevent
        it from using the bundled index.
        """
        paths = [TRAINING_INDEX_PATH]
        asset_paths_module = f"{__package__}.app.asset_paths"
        try:
            asset_paths = importlib.import_module(asset_paths_module)
        except ModuleNotFoundError as exc:
            if exc.name != asset_paths_module:
                raise
        else:
            paths.append(asset_paths.resolve_asset_file("files", TRAINING_INDEX_PATH.name))
        paths.append(TRAINING_INDEX_MOCK_PATH)
        seen: set[Path] = set()
        for path in paths:
            if path in seen:
                continue
            seen.add(path)
            try:
                with path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if isinstance(payload, dict) and isinstance(payload.get("models"), dict):
                    return payload
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        return None

    def lookup_model_training_snapshot(self, model_path: str | Path) -> Mapping[str, object] | None:
        """Find the frozen conversion context for one resolved model artifact."""
        index = self.load_training_conversion_index()
        if not index:
            return None
        artifact = Path(model_path)
        models = index.get("models")
        if not isinstance(models, Mapping):
            return None
        key = f"{artifact.parent.name}/{artifact.name}"
        snapshot = models.get(key) or models.get(artifact.name) or models.get("default")
        if not isinstance(snapshot, Mapping):
            return None
        result = dict(snapshot)
        result["is_mock"] = bool(index.get("is_mock", False))
        result.setdefault("model_artifact", artifact.name)
        return result

    @staticmethod
    def load_training_snapshot() -> Mapping[str, object] | None:
        """Return the bundled training context, if this release has one."""
        try:
            with TRAINING_SNAPSHOT_PATH.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return payload if isinstance(payload, dict) else None
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _load_runtime_snapshot(self) -> RateSnapshot:
        for path, source in (
            (_RUNTIME_RATES_PATH, "disk"),
            (_BUNDLED_RUNTIME_RATES_PATH, "bundled"),
        ):
            try:
                with path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                return self._snapshot_from_payload(payload, default_source=source)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        return RateSnapshot(**_FALLBACK)

    def _read_fresh_cache(self) -> Mapping[str, object] | None:
        try:
            with _CACHE_PATH.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            fetched_at = float(payload.get("fetched_at", 0))
            if time.time() - fetched_at < scout_rates.RATES_TTL:
                result = dict(payload)
                result["source"] = "cache"
                return result
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        return None

    @staticmethod
    def _normalize(currency: str) -> str:
        key = str(currency).strip().lower().replace("_", " ")
        aliases = {
            "e": "exalted", "exalt": "exalted", "exalted": "exalted",
            "c": "chaos", "cha": "chaos", "chaos": "chaos",
            "d": "divine", "div": "divine", "divine": "divine",
            "a": "annul", "ann": "annul", "annul": "annul", "annulment": "annul",
        }
        if key not in aliases:
            raise ValueError(f"Unsupported currency: {currency!r}")
        return aliases[key]

    @staticmethod
    def _positive(payload: Mapping[str, object], key: str, fallback: float) -> float:
        try:
            value = float(payload.get(key, fallback))
            return value if value > 0 else fallback
        except (TypeError, ValueError):
            return fallback

    def _snapshot_from_payload(
        self, payload: Mapping[str, object], *, default_source: str = "poe2scout"
    ) -> RateSnapshot:
        chaos_payload = dict(payload)
        if "chaos" not in chaos_payload and "chaos_exalt" in chaos_payload:
            chaos_payload["chaos"] = chaos_payload["chaos_exalt"]
        divine_payload = dict(payload)
        if "divine" not in divine_payload and "divine_exalt" in divine_payload:
            divine_payload["divine"] = divine_payload["divine_exalt"]
        return RateSnapshot(
            exalted=1.0,
            chaos=self._positive(chaos_payload, "chaos", _FALLBACK["chaos"]),
            divine=self._positive(divine_payload, "divine", _FALLBACK["divine"]),
            annul=self._positive(payload, "annul", _FALLBACK["annul"]),
            league=str(payload.get("league") or ""),
            source=str(payload.get("source") or default_source),
            fetched_at=payload.get("fetched_at"),
        )

    def _write_runtime_rates(self, snapshot: RateSnapshot) -> None:
        try:
            _RATES_DIR.mkdir(parents=True, exist_ok=True)
            temp = _RUNTIME_RATES_PATH.with_suffix(".json.tmp")
            temp.write_text(
                json.dumps(
                    {
                        "divine_exalt": snapshot.divine,
                        "chaos_exalt": snapshot.chaos,
                        "annul_exalt": snapshot.annul,
                        "league": snapshot.league,
                        "source": snapshot.source,
                        "refreshed_at": time.time(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            temp.replace(_RUNTIME_RATES_PATH)
        except OSError:
            _LOG.warning("Could not persist refreshed currency rates", exc_info=True)


conversion = CurrencyConversions()
prices = conversion
