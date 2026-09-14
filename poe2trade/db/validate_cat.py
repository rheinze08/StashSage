# File: poe2trade/db/validate_cat.py
# Run copy-pasted item strings through the full inference pipeline and print
# each step to the console. Intended as a quick sanity-check after training.
#
# Sample items are stored in tests/fixtures/sample_items.txt, separated by
# $$$$ on its own line.  Lines starting with # are stripped.
#
# Called from the pipeline CLI:
#   python -m poe2trade.db validate Body_Armour
#
# Or directly:
#   python tools/run_item_scoring.py [--file PATH] [--top N]

from __future__ import annotations

import io
import re
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path
from typing import Optional

from poe2trade import poe2trade_root

# ── Stub tkinter so this module can run in headless / server environments.
# config_manager imports tkinter.messagebox but only calls it in GUI error
# dialogs that are never triggered from the pipeline CLI.
if "tkinter" not in sys.modules:
    _tk_stub = types.ModuleType("tkinter")
    _tk_mb   = types.ModuleType("tkinter.messagebox")
    _tk_mb.showerror   = lambda *a, **kw: None
    _tk_mb.showinfo    = lambda *a, **kw: None
    _tk_mb.showwarning = lambda *a, **kw: None
    _tk_stub.messagebox = _tk_mb
    sys.modules["tkinter"]            = _tk_stub
    sys.modules["tkinter.messagebox"] = _tk_mb


# ── Console formatting ─────────────────────────────────────────
WIDTH = 72
SEP   = "─" * WIDTH
THICK = "═" * WIDTH


def _banner(text: str) -> None:
    print(f"\n{THICK}")
    print(f"  {text}")
    print(THICK)


def _section(label: str) -> None:
    print(f"\n{SEP}")
    print(f"  ▶  {label}")
    print(SEP)


def _kv(label: str, value) -> None:
    print(f"  {label:<30s} {value}")


# ── File loading ───────────────────────────────────────────────
_COMMENT_RE = re.compile(r"^\s*#.*$", re.MULTILINE)
_DEFAULT_FILENAME = "sample_items.txt"
_DEFAULT_FIXTURE_PATH = Path("tests") / "fixtures" / _DEFAULT_FILENAME


def _find_items_file() -> Optional[Path]:
    project_root = Path(poe2trade_root).parent
    candidates = [
        Path.cwd() / _DEFAULT_FILENAME,
        Path.cwd() / _DEFAULT_FIXTURE_PATH,
        project_root / _DEFAULT_FIXTURE_PATH,
        project_root / _DEFAULT_FILENAME,
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def load_items(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    raw = _COMMENT_RE.sub("", raw)
    blocks = re.split(r"^\s*\$\$\$\$\s*$", raw, flags=re.MULTILINE)
    return [b.strip() for b in blocks if b.strip()]


# ── Pipeline step display ──────────────────────────────────────
def show_item_text(item_text: str) -> None:
    """Step 0 - copied item text exactly as loaded from the sample document."""
    _section("STEP 0 · Item String")
    print(item_text)


def show_raw_parse(raw: dict) -> None:
    """Step 1 — direct output of parse_copied_item_text (pre-processing)."""
    _section("STEP 1 · Raw Parse")
    for k in ("Item Category", "Item Name", "Armour", "Evasion",
              "Energy Shield", "Block", "Quality", "quality_type",
              "Item Level", "Corrupted"):
        if raw.get(k) not in (None, 0, 0.0, "", "No"):
            _kv(k, raw[k])

    for prefix in ("implicit", "explicit", "rune", "enchant"):
        for i in range(1, 12):
            line = raw.get(f"{prefix}_mod_{i}")
            if line:
                _kv(f"  {prefix} {i}", line)


def show_category(cat: str, seg: "str | None", model_cat: str) -> None:
    """Step 2 — detected category, segment, and model lookup key."""
    _section("STEP 2 · Category / Segment")
    _kv("Category", cat)
    _kv("Segment", seg if seg is not None else "(none)")
    if model_cat != cat:
        _kv("Model lookup key", model_cat)


def show_features(features) -> None:
    """Step 3 — non-zero columns in the feature DataFrame sent to the model."""
    _section("STEP 3 · Feature DataFrame (non-zero columns)")
    try:
        row = features.iloc[0]
        nonzero = row[row != 0].sort_values(ascending=False)
        if nonzero.empty:
            print("  (all features are zero - check item parsing)")
        else:
            for col, val in nonzero.items():
                _kv(str(col), f"{val:.4g}")
    except Exception as exc:
        print(f"  [error reading features: {exc}]")


def show_prediction(result: "dict | None") -> None:
    """Step 4 — supervised model predictions and bucket assignment."""
    _section("STEP 4 · Supervised Prediction")
    if result is None:
        print("  No supervised models loaded (train first, or check model dir).")
        return

    for model, val in result.get("predictions", {}).items():
        _kv(f"  {model.upper()} prediction", f"{val:.2f}")

    median = result.get("median")
    if median is not None:
        _kv("Ensemble median", f"{median:.2f}")

    bucket  = result.get("bucket")
    bkt_low = result.get("bucket_low")
    bkt_hi  = result.get("bucket_high")
    color   = result.get("bucket_color_hex", "")
    if bucket:
        if bkt_low is not None and bkt_hi is not None:
            price_range = f"  [{bkt_low:.0f} – {bkt_hi:.0f}]"
        elif bkt_low is not None:
            price_range = f"  [≥ {bkt_low:.0f}]"
        elif bkt_hi is not None:
            price_range = f"  [≤ {bkt_hi:.0f}]"
        else:
            price_range = ""
        _kv("Bucket", f"{bucket}{price_range}  {color}")

    pct_vals  = result.get("percentile_values")
    pct_split = result.get("percentile_splitters")
    if pct_vals and pct_split:
        thresholds = "  /  ".join(
            f"p{s}={v:.1f}" for s, v in zip(pct_split, pct_vals)
        )
        _kv("Bucket thresholds", thresholds)


def show_similar_items(nbrs, top: int) -> None:
    """Step 5 — nearest neighbours from the KNN training overlay."""
    _section(f"STEP 5 · Similar Items (KNN, top {top})")
    if nbrs is None or (hasattr(nbrs, "__len__") and len(nbrs) == 0):
        print("  No KNN model loaded (train first, or check unsuper_models dir).")
        return
    try:
        df   = nbrs.head(top)
        want = {"price", "currency", "name", "base", "item_name", "item_base",
                "ar", "ev", "es"}
        cols = [c for c in df.columns if c.lower() in want] or list(df.columns[:6])
        col_w  = max(14, *(len(c) for c in cols))
        header = "  " + "  ".join(f"{c:<{col_w}}" for c in cols)
        print(header)
        print("  " + "-" * (len(header) - 2))
        for _, row in df.iterrows():
            print("  " + "  ".join(f"{str(row.get(c, '')):<{col_w}}" for c in cols))
    except Exception as exc:
        print(f"  [error displaying similar items: {exc}]")


# ── PDF export ─────────────────────────────────────────────────
_LINES_PER_PAGE = 55
_PDF_FONT_SIZE  = 7.5


def _write_pdf(text: str, pdf_path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
    except ImportError:
        print("[PDF] matplotlib not available - skipping PDF export.")
        return

    lines = text.splitlines()
    pages = [lines[i: i + _LINES_PER_PAGE] for i in range(0, max(len(lines), 1), _LINES_PER_PAGE)]

    with PdfPages(pdf_path) as pdf:
        for page_lines in pages:
            fig, ax = plt.subplots(figsize=(11, 8.5))
            ax.axis("off")
            ax.text(
                0.01, 0.99,
                "\n".join(page_lines),
                transform=ax.transAxes,
                fontsize=_PDF_FONT_SIZE,
                fontfamily="monospace",
                verticalalignment="top",
                wrap=False,
            )
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    print(f"[PDF] Validation report written to: {pdf_path}")


# ── Core runner ────────────────────────────────────────────────
def run_items(
    items: list[str],
    categories: list[str],
    top: int = 5,
    pdf_path: Optional[Path] = None,
) -> None:
    """Run a list of item text blocks through the inference pipeline."""
    from poe2trade.utils.gui_utils import (
        prepare_item_features,
        call_super_prepared,
        call_unsuper_prepared,
    )

    cat_filter = {c.lower().replace(" ", "_") for c in categories} if categories else set()
    scored = 0
    skipped = 0

    buf: Optional[io.StringIO] = io.StringIO() if pdf_path else None

    real_stdout = sys.stdout

    class _Tee(io.TextIOBase):
        """Write to both the real stdout and the capture buffer."""
        def write(self, s: str) -> int:
            real_stdout.write(s)
            buf.write(s)  # type: ignore[union-attr]
            return len(s)
        def flush(self) -> None:
            real_stdout.flush()

    out = _Tee() if buf is not None else real_stdout

    with redirect_stdout(out):
        for idx, item_text in enumerate(items, start=1):
            first_line = next(
                (ln.strip() for ln in item_text.splitlines() if ln.strip()),
                "(empty)"
            )

            try:
                prepared = prepare_item_features(item_text)
            except Exception as exc:
                print(f"\n[WARN] Item {idx} - prepare_item_features failed: {exc}")
                skipped += 1
                continue

            if cat_filter and prepared.category not in cat_filter:
                skipped += 1
                continue

            scored += 1
            _banner(f"ITEM {idx}  —  {first_line}")
            show_item_text(item_text)
            show_raw_parse(prepared.raw_parsed)
            show_category(prepared.category, prepared.segment, prepared.model_category)
            show_features(prepared.features)

            try:
                result = call_super_prepared(prepared)
            except Exception as exc:
                result = None
                print(f"\n  [supervised model error: {exc}]")
            show_prediction(result)

            try:
                _, nbrs = call_unsuper_prepared(prepared)
            except Exception as exc:
                nbrs = None
                print(f"\n  [KNN model error: {exc}]")
            show_similar_items(nbrs, top=top)

        print(f"\n{THICK}")
        print(f"  Done - {scored} item(s) scored, {skipped} skipped.")
        print(f"{THICK}\n")

    if buf is not None and pdf_path is not None:
        _write_pdf(buf.getvalue(), pdf_path)


# ── Pipeline entry point ───────────────────────────────────────
def main(
    categories: list[str],
    *,
    items_file: Optional[Path] = None,
    top: int = 5,
    pdf_path: Optional[Path] = None,
) -> None:
    """
    Validate the inference pipeline against sample items.

    Parameters
    ----------
    categories : list[str]
        If non-empty, only items whose detected category matches are scored.
        Pass an empty list to score every item in the file.
    items_file : Path | None
        Path to the sample items txt file. Defaults to
        tests/fixtures/sample_items.txt, with current-directory and legacy
        project-root fallbacks.
    top : int
        Number of KNN neighbours to display per item.
    pdf_path : Path | None
        If provided, the full validation report is also written to this PDF.
    """
    path = items_file or _find_items_file()
    if path is None:
        print(
            f"[validate] No items file found.  "
            f"Create '{_DEFAULT_FIXTURE_PATH}' and add items "
            f"separated by $$$$ on its own line."
        )
        return

    items = load_items(path)
    if not items:
        print(f"[validate] No item blocks found in {path}  "
              f"(separate items with $$$$ on its own line)")
        return

    print(f"\n[validate] {len(items)} item(s) from {path}")
    if categories:
        normalised = [c.lower().replace(" ", "_") for c in categories]
        print(f"[validate] Filtering to categories: {normalised}")

    run_items(items, categories, top=top, pdf_path=pdf_path)
