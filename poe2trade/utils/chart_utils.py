# poe2trade/utils/chart_utils.py
"""
chart_utils.py - helper plots for price history, offers table, and
bucket-confidence visualisation.

Changes (7 Sep 2025)
- Canonical currency mapping for robust dual-axis selection.
- Per-item, per-offer dedupe: keep only the latest (buyer, amount, currency).
- Fixed canvas preserved (6x4 in @ 96 dpi).
"""
from __future__ import annotations

import io
import json
from datetime import datetime
from functools import lru_cache
from typing import Mapping, Sequence, Tuple

import warnings

import numpy as np
import pandas as pd

# NOTE: matplotlib is intentionally NOT imported at module level. Importing it
# (plus the font-manager scan below) costs ~400 ms of cold startup, and this
# module is pulled in by both the GUI and the Flask API before any chart is
# requested. ensure_matplotlib() imports & configures it on first render.

# Display constants used across plot helpers
FIG_W_IN = 6          # width  in inches ~= 576 px at 96 dpi
FIG_H_IN = 4          # height in inches ~= 384 px at 96 dpi
FIG_DPI  = 96
# +----------------------------------------------------------------------+

# Unicode-friendly default font stack
# Prefer fonts with broader Unicode coverage, especially Thai on Windows.
_PREFERRED_SANS_SERIF = [
    "Leelawadee UI",  # Windows Thai UI font
    "Tahoma",         # Broad coverage incl. Thai
    "Segoe UI",
    "Noto Sans Thai",
    "Noto Sans",
    "DejaVu Sans",
    "Arial Unicode MS",
    "Microsoft YaHei",
    "SimHei",
]


import threading as _threading
_MPL_LOCK = _threading.Lock()


@lru_cache(maxsize=1)
def _import_matplotlib():
    """Import matplotlib and configure it for headless rendering.

    Returns (mpl, plt, patches). All charts are saved to PNG buffers, never
    shown interactively, so the Agg backend is forced (this also matches the
    backend the Flask API previously set at import time and keeps figure
    creation safe from worker threads).
    """
    import matplotlib as mpl
    mpl.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib import font_manager as fm

    try:
        installed = {f.name for f in fm.fontManager.ttflist}
    except Exception:
        installed = set()
    # Same effective font config the app had when these rcParams were applied
    # at import time (discord_flask set font.family last, so it won) -- but
    # only name fonts that are actually installed, so matplotlib does not log
    # a slow findfont warning for every rendered glyph.
    family = [n for n in ("Microsoft YaHei", "DejaVu Sans") if n in installed]
    mpl.rcParams["font.family"] = family or "sans-serif"
    # Tighten the sans-serif fallback list to installed fonts, keeping order.
    stack = [name for name in _PREFERRED_SANS_SERIF if name in installed]
    mpl.rcParams["font.sans-serif"] = stack or _PREFERRED_SANS_SERIF

    return mpl, plt, patches


def ensure_matplotlib():
    """Lazy, thread-safe matplotlib accessor; see _import_matplotlib()."""
    with _MPL_LOCK:
        return _import_matplotlib()


def _save_png(fig) -> io.BytesIO:
    """Save a figure to PNG, suppressing noisy missing-glyph warnings."""
    _, plt, _ = ensure_matplotlib()
    buf = io.BytesIO()
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"Glyph \d+ .* missing from font",
            category=UserWarning,
        )
        fig.savefig(
            buf, format="png", dpi=FIG_DPI,
            facecolor=fig.get_facecolor(), bbox_inches=None,
        )
    plt.close(fig)
    buf.seek(0)
    return buf


def _buf_from_bytes(data: bytes) -> io.BytesIO:
    buf = io.BytesIO(data)
    buf.seek(0)
    return buf


def _rounded_float(value: float | None, ndigits: int = 3) -> float | None:
    if not isinstance(value, (int, float)) or not np.isfinite(float(value)):
        return None
    return round(float(value), ndigits)


def _apply_readable_price_scale(ax, low: float, high: float) -> str:
    """Use a log-like x scale when a price tail would flatten the main mass."""
    if not (np.isfinite(low) and np.isfinite(high)) or high <= low:
        return "Predicted Price (exalts)"
    positive_low = low if low > 0 else max(1.0, high * 0.002)
    if positive_low > 0 and high / positive_low >= 25:
        # ``symlog`` preserves a readable zero/low-price region while making
        # expensive outliers visible without flattening the ordinary listings.
        ax.set_xscale("symlog", linthresh=max(1.0, min(20.0, positive_low)))
        return "Predicted Price (exalts, log scale)"
    return "Predicted Price (exalts)"


def generate_prediction_vs_listings_chart(
    prediction: float | None,
    listing_prices: Sequence[float],
    *,
    title: str = "Your prediction vs nearest listings",
    width: float = 9.4,
    height: float = 3.1,
) -> io.BytesIO:
    """Show the decision-relevant price context for the active item.

    This intentionally uses the nearest listings already selected for Model #2
    rather than the broad training distribution. It answers whether Model #1's
    estimate is above, below, or inside the observed comparable-price cluster.
    """
    _, plt, _ = ensure_matplotlib()
    values = np.asarray([float(value) for value in listing_prices if np.isfinite(float(value)) and float(value) > 0])
    fig, ax = plt.subplots(figsize=(width, height), dpi=FIG_DPI, facecolor="white")
    if values.size == 0:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "No comparable listing prices", ha="center", va="center")
        return _save_png(fig)

    values.sort()
    y = np.zeros(values.size)
    ax.scatter(values, y, s=75, color="#377EAA", edgecolor="#173548", linewidth=1.0, zorder=3, label="Nearest listings")
    for index, value in enumerate(values):
        ax.annotate(f"{value:.0f}e", (value, 0), xytext=(0, 12 + (index % 2) * 13), textcoords="offset points", ha="center", fontsize=8, color="#234E69")
    median = float(np.median(values))
    mean = float(np.mean(values))
    ax.axvline(median, color="#6E4EA1", linewidth=2, linestyle="--", label=f"Median {median:.1f}e")
    ax.axvline(mean, color="#D0882C", linewidth=2, linestyle=":", label=f"Mean {mean:.1f}e")
    if prediction is not None and isinstance(prediction, (int, float)) and np.isfinite(float(prediction)) and float(prediction) > 0:
        value = float(prediction)
        ax.axvline(value, color="#C24B48", linewidth=2.6, label=f"Your prediction {value:.1f}e")
    low = min(float(values.min()), float(prediction) if isinstance(prediction, (int, float)) and prediction > 0 else float(values.min()))
    high = max(float(values.max()), float(prediction) if isinstance(prediction, (int, float)) and prediction > 0 else float(values.max()))
    pad = max((high - low) * .12, low * .08, 1.0)
    ax.set_xlim(max(0.01, low - pad), high + pad)
    ax.set_ylim(-0.45, 0.62)
    ax.set_yticks([])
    ax.set_xlabel(_apply_readable_price_scale(ax, low, high))
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.legend(loc="lower center", ncol=4, fontsize=8, frameon=False)
    ax.grid(axis="x", color="#D7DDE1", alpha=.55)
    fig.tight_layout()
    return _save_png(fig)

# New: single overlay with a vertical marker for the current item's value
def generate_predicted_overlay_with_marker(
    df_scored: pd.DataFrame,
    marker_value: float | None,
    *,
    title: str | None = None,
    # 50% larger defaults for sharper display when scaled in UI
    width: float = FIG_W_IN * 2.4,
    height: float = FIG_H_IN * 1.2,
    bins: int = 30,
) -> io.BytesIO:
    """
    Build a single-subplot overlay of predicted distributions by bucket and
    draw a vertical dashed line at `marker_value` (e.g. the item's xgboost
    prediction) to show relative position.
    Expects df_scored to include columns: 'bucket_label', 'pred_median'.
    """
    _, plt, _ = ensure_matplotlib()
    if df_scored is None or df_scored.empty:
        # fallback empty fig
        fig, ax = plt.subplots(figsize=(width, height), dpi=FIG_DPI, facecolor="white")
        ax.set_axis_off()
        ax.text(0.5, 0.5, "No data for distributions", ha="center", va="center")
        return _save_png(fig)

    df = df_scored.copy()
    df.columns = [str(c).lower() for c in df.columns]
    if "bucket_label" not in df.columns or "pred_median" not in df.columns:
        fig, ax = plt.subplots(figsize=(width, height), dpi=FIG_DPI, facecolor="white")
        ax.set_axis_off()
        ax.text(0.5, 0.5, "Missing columns for distributions", ha="center", va="center")
        return _save_png(fig)

    buckets = ("Low", "Medium", "High")
    pred_by_bucket = {
        lbl: df.loc[df["bucket_label"] == lbl, "pred_median"].dropna().to_numpy()
        for lbl in buckets
    }
    all_pred = np.concatenate([v for v in pred_by_bucket.values() if len(v) > 0]) if any(len(v) for v in pred_by_bucket.values()) else np.array([])

    fig, ax = plt.subplots(figsize=(width, height), dpi=FIG_DPI, facecolor="white")
    if all_pred.size:
        # common bins across all buckets
        p_lo, p_hi = np.percentile(all_pred, [1, 99]) if all_pred.size >= 10 else (float(np.min(all_pred)), float(np.max(all_pred)))
        if not np.isfinite(p_lo) or not np.isfinite(p_hi) or p_lo == p_hi:
            p_lo, p_hi = float(np.min(all_pred)), float(np.max(all_pred) + 1e-9)
        edges = np.linspace(p_lo, p_hi, max(5, bins))
        colours = {"Low": "#E74C3C", "Medium": "#F39C12", "High": "#27AE60"}
        max_share = 0.0
        for lbl in buckets:
            vals = pred_by_bucket[lbl]
            if len(vals):
                # Compare the *shape* of each bucket, not raw training-set
                # population. Raw counts made the plot primarily a chart of
                # class imbalance and hid the item's useful price context.
                weights = np.full(len(vals), 100.0 / len(vals))
                counts, _, patches = ax.hist(
                    vals,
                    bins=edges,
                    weights=weights,
                    color=colours.get(lbl),
                    alpha=0.28,
                    edgecolor="none",
                    label=f"{lbl} price shape",
                )
                ax.hist(
                    vals,
                    bins=edges,
                    weights=weights,
                    histtype="step",
                    color=colours.get(lbl),
                    linewidth=1.8,
                )
                if counts.size:
                    max_share = max(max_share, float(counts.max()))
        # Set initial limits to distribution range
        ax.set_xlim(p_lo, p_hi)
        if max_share > 0:
            ax.set_ylim(0, max_share * 1.1)
        ax.set_xlabel(_apply_readable_price_scale(ax, p_lo, p_hi))
        ax.set_ylabel("Share of bucket (%)")
        ax.legend(loc="upper right")
    else:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "No distribution data", ha="center", va="center")

    if marker_value is not None and isinstance(marker_value, (int, float)):
        try:
            mv = float(marker_value)
            # Ensure the marker is within view: expand x-limits if necessary
            x0, x1 = ax.get_xlim()
            if np.isfinite(mv) and (mv < x0 or mv > x1):
                pad = (x1 - x0) * 0.02 if x1 > x0 else 1.0
                ax.set_xlim(min(x0, mv) - pad, max(x1, mv) + pad)
            ax.axvline(mv, linestyle="--", color="black", linewidth=2, alpha=0.8)
            ymax = ax.get_ylim()[1]
            label = f"Your item\n{mv:,.0f}e"
            ax.text(
                mv,
                ymax * 0.75,  # Keep the marker label below the bucket legend.
                label,
                rotation=90,
                va="top",
                ha="right",
                fontsize=8,
                color="black",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.6, edgecolor="none"),
            )
        except Exception:
            pass

    if not title:
        title = "Price context by model bucket"
    ax.set_title(title, fontsize=11, fontweight="bold")

    fig.tight_layout()
    return _save_png(fig)


def generate_predicted_overlay_from_profile(
    profile: Mapping[str, object],
    marker_value: float | None,
    *,
    title: str | None = None,
    width: float = FIG_W_IN * 2.4,
    height: float = FIG_H_IN * 1.2,
) -> io.BytesIO:
    try:
        profile_key = json.dumps(profile, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        profile_key = str(profile)
    return _buf_from_bytes(
        _generate_predicted_overlay_from_profile_cached(
            profile_key,
            _rounded_float(marker_value),
            title or "",
            float(width),
            float(height),
        )
    )


@lru_cache(maxsize=16)
def _generate_predicted_overlay_from_profile_cached(
    profile_json: str,
    marker_value: float | None,
    title: str,
    width: float,
    height: float,
) -> bytes:
    """
    Render the predicted distribution overlay from pre-binned profile data.

    The profile is generated during scoring from the same pred_median values
    used by generate_predicted_overlay_with_marker, so runtime rendering can
    preserve the distribution shape without loading every scored row.
    """
    _, plt, _ = ensure_matplotlib()
    try:
        profile = json.loads(profile_json)
    except Exception:
        profile = {}
    try:
        edges = np.asarray(profile.get("bin_edges"), dtype=float)  # type: ignore[arg-type]
        raw_counts = profile.get("bucket_counts")  # type: ignore[assignment]
        if edges.ndim != 1 or edges.size < 2 or not isinstance(raw_counts, Mapping):
            raise ValueError("invalid profile")
    except Exception:
        fig, ax = plt.subplots(figsize=(width, height), dpi=FIG_DPI, facecolor="white")
        ax.set_axis_off()
        ax.text(0.5, 0.5, "No distribution data", ha="center", va="center")
        return _save_png(fig).getvalue()

    buckets = ("Low", "Medium", "High")
    colours = {"Low": "#E74C3C", "Medium": "#F39C12", "High": "#27AE60"}
    totals = profile.get("bucket_totals") if isinstance(profile.get("bucket_totals"), Mapping) else {}
    widths = np.diff(edges)
    fig, ax = plt.subplots(figsize=(width, height), dpi=FIG_DPI, facecolor="white")
    max_share = 0.0
    plotted = False

    for lbl in buckets:
        raw = raw_counts.get(lbl.lower()) if isinstance(raw_counts, Mapping) else None
        try:
            counts = np.asarray(raw, dtype=float)
        except Exception:
            continue
        if counts.size != widths.size:
            continue
        total = None
        if isinstance(totals, Mapping):
            try:
                total = int(totals.get(lbl.lower(), int(counts.sum())))
            except Exception:
                total = int(counts.sum())
        count_total = float(counts.sum())
        if count_total <= 0:
            continue
        shares = counts * (100.0 / count_total)
        if shares.size:
            max_share = max(max_share, float(shares.max()))
        if np.any(counts):
            plotted = True
            ax.bar(
                edges[:-1],
                shares,
                width=widths,
                align="edge",
                color=colours.get(lbl),
                alpha=0.28,
                edgecolor="none",
                label=f"{lbl} price shape",
            )
            y_edges = np.r_[shares, shares[-1]]
            ax.step(edges, y_edges, where="post", color=colours.get(lbl), linewidth=1.8)

    if plotted:
        ax.set_xlim(float(edges[0]), float(edges[-1]))
        if max_share > 0:
            ax.set_ylim(0, max_share * 1.1)
        ax.set_xlabel(_apply_readable_price_scale(ax, float(edges[0]), float(edges[-1])))
        ax.set_ylabel("Share of bucket (%)")
        ax.legend(loc="upper right")
    else:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "No distribution data", ha="center", va="center")

    if marker_value is not None and isinstance(marker_value, (int, float)):
        try:
            mv = float(marker_value)
            x0, x1 = ax.get_xlim()
            if np.isfinite(mv) and (mv < x0 or mv > x1):
                pad = (x1 - x0) * 0.02 if x1 > x0 else 1.0
                ax.set_xlim(min(x0, mv) - pad, max(x1, mv) + pad)
            ax.axvline(mv, linestyle="--", color="black", linewidth=2, alpha=0.8)
            ymax = ax.get_ylim()[1]
            ax.text(
                mv,
                ymax * 0.75,  # Keep the marker label below the bucket legend.
                f"Your item\n{mv:,.0f}e",
                rotation=90,
                va="top",
                ha="right",
                fontsize=8,
                color="black",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.6, edgecolor="none"),
            )
        except Exception:
            pass

    ax.set_title(title or "Price context by model bucket", fontsize=11, fontweight="bold")
    fig.tight_layout()
    return _save_png(fig).getvalue()

# -- currency helpers ---------------------------------------------------
def _canon_cur(s: str) -> str:
    s = (s or "").strip().lower()
    if s.startswith("ex"):
        return "exalted"
    if s.startswith("chaos") or s.startswith("c"):
        return "chaos"
    if s.startswith("div"):
        return "divine"
    return s or "chaos"

def _cur_letter(s: str) -> str:
    s = _canon_cur(s)
    return {"exalted": "E", "chaos": "C", "divine": "D"}.get(s, s[:1].upper())

# -----------------------------------------------------------------------
# 1 ? PRICE-HISTORY CHART
# -----------------------------------------------------------------------
def generate_price_chart_for_item(
    item_name      : str,
    df_trades: pd.DataFrame,
    item_col       : str = "item_name",
    *_,
    predicted_mean   : float | None = None,   # kept for API compat
    predicted_median : float | None = None,
    predicted_min    : float | None = None,
    predicted_max    : float | None = None,
    bucket_label     : str   | None = None,
    bucket_median    : float | None = None,
    **__,            # swallow legacy kwargs
) -> io.BytesIO:
    """Fixed-size, two-axis price plot; dedupes duplicate offers to latest."""
    _, plt, _ = ensure_matplotlib()
    fig, ax_left = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN),
                                dpi=FIG_DPI, facecolor="white")
    ax_right = None

    # -- subset for this item -------------------------------------------
    if df_trades.empty:
        ax_left.text(0.5, 0.5, "No offer history for this item",
                     ha="center", va="center", fontsize=12)
    else:
        df = df_trades.copy()
        if not np.issubdtype(df["timestamp"].dtype, np.datetime64):
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        df[item_col] = df[item_col].astype(str)
        mask = df[item_col].str.replace(",", "").str.lower() == item_name.replace(",", "").lower()
        df_item = df.loc[mask].copy()

        if df_item.empty:
            ax_left.text(0.5, 0.5, "No offer history for this item",
                         ha="center", va="center", fontsize=12)
        else:
            # canonicalize currency & dedupe to latest per (buyer, amount, currency)
            df_item["currency"] = df_item["currency"].astype(str)
            df_item["cur_canon"] = df_item["currency"].map(_canon_cur)
            df_item.sort_values("timestamp", inplace=True)
            df_item = (df_item
                       .dropna(subset=["buyer","amount","cur_canon"])
                       .drop_duplicates(subset=["buyer","amount","cur_canon"], keep="last"))

            # choose axes currencies
            cur_set = list(sorted(df_item["cur_canon"].unique()))
            cur_left = cur_right = None
            if len(cur_set) == 1:
                cur_left = cur_set[0]
            elif len(cur_set) >= 2:
                # prefer exalted on left if present
                if "exalted" in cur_set:
                    cur_left = "exalted"
                    cur_right = next((c for c in cur_set if c != "exalted"), cur_set[0])
                else:
                    cur_left, cur_right = cur_set[:2]

            df_item["x_date"] = df_item["timestamp"].dt.floor("D")

            def _plot(dfc, ax, marker, style, lbl, color):
                ax.plot(dfc["x_date"], dfc["amount"],
                        marker=marker, linestyle=style,
                        label=lbl, color=color)

            # left axis
            if cur_left:
                left_df = df_item[df_item["cur_canon"] == cur_left]
                if not left_df.empty:
                    _plot(left_df, ax_left, "o", "-", _cur_letter(cur_left), "tab:blue")
                    ax_left.set_ylabel(_cur_letter(cur_left),
                                       color="tab:blue", fontsize=8)
                    ax_left.tick_params(axis="y", colors="tab:blue")

            # right axis
            if cur_right:
                ax_right = ax_left.twinx()
                right_df = df_item[df_item["cur_canon"] == cur_right]
                if not right_df.empty:
                    _plot(right_df, ax_right, "s", "--", _cur_letter(cur_right), "tab:red")
                    ax_right.set_ylabel(_cur_letter(cur_right),
                                        color="tab:red", fontsize=8)
                    ax_right.tick_params(axis="y", colors="tab:red")

            # legend at bottom
            h_left,  l_left  = ax_left.get_legend_handles_labels()
            h_right, l_right = ax_right.get_legend_handles_labels() if ax_right else ([], [])
            if h_left or h_right:
                fig.legend(h_left + h_right, l_left + l_right,
                           loc="upper center", bbox_to_anchor=(0.5, 0.02),
                           ncol=2, fontsize=8, frameon=False)

            # x-axis by unique date
            dates = sorted(df_item["x_date"].unique())
            ax_left.set_xticks(dates)
            ax_left.set_xticklabels([pd.Timestamp(d).strftime("%m-%d") for d in dates],
                                    rotation=90, ha="center", fontsize=7)

    # title
    ax_left.set_title(f"Offer History for\n{item_name}",
                      fontsize=12, fontweight="bold")

    # grids off
    ax_left.grid(False);  ax_right.grid(False) if ax_right else None

    # keep room for title + rotated dates
    fig.tight_layout()
    plt.subplots_adjust(top=0.86, bottom=0.24)

    return _save_png(fig)

# -----------------------------------------------------------------------
# 2 ? LAST-OFFERS TABLE  (dedup latest per buyer/amount/currency)
# -----------------------------------------------------------------------
def generate_offers_table_chart(
    item_name       : str,
    df_trades: pd.DataFrame,
    item_col        : str = "item_name",
    *,
    predicted_price : float | None = None,
    difference      : float = 0.0,
    show_legacy_text: bool  = False,
    **__,
) -> io.BytesIO:
    _, plt, patches = ensure_matplotlib()
    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN),
                           dpi=FIG_DPI, facecolor="white")
    ax.set_axis_off()

    title = f"Last 5 Offers for\n{item_name}"
    placeholder_printed = False
    if df_trades.empty:
        ax.text(0.5, 0.5, "No offer history for this item",
                ha="center", va="center", fontsize=12)
        placeholder_printed = True
    if not df_trades.empty:
        df = df_trades.copy()
        if not np.issubdtype(df["timestamp"].dtype, np.datetime64):
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        df[item_col] = df[item_col].astype(str)
        mask = df[item_col].str.replace(",", "").str.lower() == item_name.replace(",", "").lower()
        df_item = df.loc[mask].copy()

        if not df_item.empty:
            df_item["cur_canon"] = df_item["currency"].astype(str).map(_canon_cur)
            df_item.sort_values("timestamp", inplace=True)
            dedup = (df_item
                     .dropna(subset=["buyer","amount","cur_canon"])
                     .drop_duplicates(subset=["buyer","amount","cur_canon"], keep="last")
                     .sort_values("timestamp", ascending=False)
                     .head(5))

            if not dedup.empty:
                now = datetime.now()
                dedup["Days Ago"] = ((now - dedup["timestamp"]).dt.total_seconds() / 86400).round(1)
                dedup["Cur"] = dedup["cur_canon"].map(_cur_letter)

                cells = dedup[["buyer", "amount", "Cur", "Days Ago"]].astype(str).values
                table = ax.table(
                    cellText=cells,
                    colLabels=["Buyer", "Offer", "Cur", "Days Ago"],
                    loc="center",
                    cellLoc="center",
                    colColours=["#dddddd"] * 4,
                )
                for cell in table.get_celld().values():
                    cell.set_edgecolor("black")
                    cell.set_linewidth(1)
                table.auto_set_font_size(False)
                table.set_fontsize(10)
                table.scale(1, 1.4)
            else:
                if not placeholder_printed:
                    ax.text(0.5, 0.5, "No offer history for this item",
                            ha="center", va="center", fontsize=12)
                    placeholder_printed = True
        else:
            if not placeholder_printed:
                ax.text(0.5, 0.5, "No offer history for this item",
                        ha="center", va="center", fontsize=12)
                placeholder_printed = True

    ax.add_patch(patches.Rectangle((0, 0), 1, 1,
                                   transform=ax.transAxes,
                                   fill=False, linewidth=1, edgecolor="black"))
    plt.title(title, fontsize=12, fontweight="bold", pad=15)

    fig.tight_layout()
    return _save_png(fig)

# -----------------------------------------------------------------------
# 3 ? BUCKET-CONFIDENCE PLOT (unchanged logic)
# -----------------------------------------------------------------------
_BUCKET_COLOURS = {"low": "#E74C3C", "medium": "#F39C12", "high": "#27AE60"}

def generate_bucket_confidence_plot(
    *,
    pred_median : float,
    intervals   : Mapping[str, Tuple[float | None, float | None]],
    bucket_label: str,
    **__,
) -> io.BytesIO:
    try:
        intervals_key = json.dumps(intervals, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        intervals_key = str(intervals)
    return _buf_from_bytes(
        _generate_bucket_confidence_plot_cached(
            _rounded_float(pred_median),
            intervals_key,
            str(bucket_label or ""),
        )
    )


@lru_cache(maxsize=16)
def _generate_bucket_confidence_plot_cached(
    pred_median: float | None,
    intervals_json: str,
    bucket_label: str,
) -> bytes:
    _, plt, _ = ensure_matplotlib()
    try:
        raw_intervals = json.loads(intervals_json)
        intervals = {
            str(k): tuple(v) if isinstance(v, list) else v
            for k, v in raw_intervals.items()
        }
    except Exception:
        intervals = {}
    pred_median = float(pred_median or 0.0)
    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN),
                           dpi=FIG_DPI, facecolor="white")

    y_pos = {"high": 0, "medium": 1, "low": 2}
    lo_vals, hi_vals = [], []

    for key, (lo, hi) in intervals.items():
        if lo is None or hi is None:
            continue
        col = _BUCKET_COLOURS[key]
        ypos = y_pos[key]
        ax.fill_betweenx([ypos - 0.35, ypos + 0.35], lo, hi,
                         color=col, alpha=0.15)
        lw = 6 if key == bucket_label.lower() else 3
        ax.hlines(ypos, lo, hi, color=col, linewidth=lw)
        ax.plot([lo, hi], [ypos, ypos],
                linestyle="None", marker="|", markersize=10, color=col)
        lo_vals.append(lo); hi_vals.append(hi)

    ax.plot(pred_median, y_pos.get(bucket_label.lower(), 1),
            marker="v", color="black", markersize=9)

    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["High", "Medium", "Low"], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Exalts", fontsize=9)
    ax.set_title("80 % Confidence Intervals", fontsize=10, fontweight="bold")
    ax.grid(False)

    if lo_vals and hi_vals:
        ax.set_xlim(max(0, min(lo_vals) * 0.9), max(hi_vals) * 1.1)
    else:
        ax.set_xlim(left=max(0, pred_median * 0.3))

    fig.tight_layout()
    return _save_png(fig).getvalue()
