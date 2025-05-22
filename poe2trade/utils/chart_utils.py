"""
chart_utils.py – helper plots for price history, offers table, and
bucket-confidence visualisation.

All helpers return an in-memory PNG (io.BytesIO).
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Mapping, Tuple

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ────────────────────────────────────────────────────────────────────────
# defaults
# ────────────────────────────────────────────────────────────────────────
DEFAULT_IMG_WIDTH_INCHES  = 4.0
DEFAULT_IMG_HEIGHT_INCHES = 3.0


# ────────────────────────────────────────────────────────────────────────
# 1 ▸ historical price chart (title has **no numbers**)
# ────────────────────────────────────────────────────────────────────────
def generate_price_chart_for_item(
    item_name: str,
    df_trades,
    item_col: str = "item_name",
    *,
    predicted_mean:   float | None = None,
    predicted_median: float | None = None,
    predicted_min:    float | None = None,
    predicted_max:    float | None = None,
    bucket_label:     str   | None = None,
    bucket_median:    float | None = None,
    width:  float = DEFAULT_IMG_WIDTH_INCHES,
    height: float = DEFAULT_IMG_HEIGHT_INCHES,
) -> io.BytesIO:
    """Offer-history plot – clean title, fixed canvas size."""
    fig, ax1 = plt.subplots(figsize=(width, height), facecolor="white")
    ax2 = None

    if df_trades.empty:
        ax1.text(0.5, 0.5, "No trade history",
                 ha="center", va="center", fontsize=12)
    else:
        df_item = df_trades[
            df_trades[item_col].str.replace(",", "").str.lower()
            == item_name.replace(",", "").lower()
        ].copy()

        if df_item.empty:
            ax1.text(0.5, 0.5, "No trade history for this item",
                     ha="center", va="center", fontsize=12)
        else:
            df_item.sort_values("timestamp", inplace=True)
            df_item["currency"] = df_item["currency"].str.lower()

            df_ex  = df_item[df_item["currency"] == "exalted"].copy()
            df_div = df_item[df_item["currency"] == "divine" ].copy()
            for d in (df_item, df_ex, df_div):
                d["x_date"] = d["timestamp"].dt.floor("D")

            # ── plot Exalts (left axis) ────────────────────────────────
            if not df_ex.empty:
                ax1.plot(df_ex["x_date"], df_ex["amount"],
                         marker="o", linestyle="-",
                         label="Exalted", color="tab:blue")
                ax1.set_ylabel("Exalts", fontsize=8, color="tab:blue")
                ax1.tick_params(axis="y", colors="tab:blue")

            # ── plot Divines (right axis) ──────────────────────────────
            if not df_div.empty:
                ax2 = ax1.twinx()
                ax2.plot(df_div["x_date"], df_div["amount"],
                         marker="s", linestyle="--",
                         label="Divine", color="tab:red")
                ax2.set_ylabel("Divines", fontsize=8, color="tab:red")
                ax2.tick_params(axis="y", colors="tab:red")

            # ── legend (handles from *both* axes) ─────────────────────
            if not df_ex.empty or not df_div.empty:
                h1, l1 = ax1.get_legend_handles_labels()
                h2, l2 = (ax2.get_legend_handles_labels() if ax2 else ([], []))
                fig.legend(
                    h1 + h2, l1 + l2,
                    loc="upper center",
                    bbox_to_anchor=(0.5, 0.02),       # inside the figure
                    bbox_transform=fig.transFigure,
                    ncol=2,
                    fontsize=8,
                    frameon=False,
                )

            # ── tidy x-axis dates ─────────────────────────────────────
            x_dates = sorted(df_item["x_date"].unique())
            ax1.set_xticks(x_dates)
            ax1.set_xticklabels([d.strftime("%m-%d") for d in x_dates],
                                rotation=90, fontsize=7, ha="center")

    ax1.set_title(f"Offer History for\n{item_name}",
                  fontsize=10, fontweight="bold")
    ax1.grid(False)
    if ax2:
        ax2.grid(False)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.22)          # space for legend
    buf = io.BytesIO()
    plt.savefig(buf, format="png", facecolor=fig.get_facecolor())  # fixed canvas
    buf.seek(0)
    plt.close(fig)
    return buf


# ────────────────────────────────────────────────────────────────────────
# 2 ▸ last-offers table  (unchanged)
# ────────────────────────────────────────────────────────────────────────
def generate_offers_table_chart(
    item_name: str,
    df_trades,
    item_col: str = "item_name",
    *,
    predicted_price: float | None = None,
    difference:      float = 0.0,
    width:  float = DEFAULT_IMG_WIDTH_INCHES,
    height: float = DEFAULT_IMG_HEIGHT_INCHES,
    show_legacy_text: bool = False,
) -> io.BytesIO:
    """“Last 5 offers” table – fixed canvas size."""
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_axis_off()

    if df_trades.empty:
        ax.text(0.5, 0.5, "No trade history",
                ha="center", va="center", fontsize=12)
        plt.title(f"Last 5 Offers for\n{item_name}",
                  fontsize=12, fontweight="bold", pad=15)
    else:
        df_item = df_trades[
            df_trades[item_col].str.replace(",", "").str.lower()
            == item_name.replace(",", "").lower()
        ].copy()

        if df_item.empty:
            ax.text(0.5, 0.5, "No trade offers for this item",
                    ha="center", va="center", fontsize=12)
            plt.title(f"Last 5 Offers for\n{item_name}",
                      fontsize=12, fontweight="bold", pad=15)
        else:
            df_item.sort_values("timestamp", inplace=True)
            df_item["buyer"] = df_item["buyer"].str.slice(stop=10)
            grp = (
                df_item.groupby("buyer")
                .agg({"timestamp": "max", "amount": "max"})
                .reset_index()
                .sort_values("timestamp", ascending=False)
                .head(5)
            )
            if grp.empty:
                ax.text(0.5, 0.5, "No recent offers",
                        ha="center", va="center", fontsize=12)
            else:
                now = datetime.now()
                grp["Days Ago"] = (
                    (now - grp["timestamp"]).dt.total_seconds() / 86_400
                ).round(1)
                cell = grp[["buyer", "amount", "Days Ago"]].astype(str).values
                tbl = ax.table(
                    cellText=cell,
                    colLabels=["Buyer", "Offer", "Days Ago"],
                    loc="center",
                    cellLoc="center",
                    colColours=["#dddddd"] * 3,
                )
                for _, c in tbl.get_celld().items():
                    c.set_linewidth(1)
                    c.set_edgecolor("black")
                tbl.auto_set_font_size(False)
                tbl.set_fontsize(10)
                tbl.scale(1, 1.4)

            plt.title(f"Last 5 Offers for\n{item_name}",
                      fontsize=12, fontweight="bold", pad=15)

    if show_legacy_text and predicted_price is not None:
        color = "green" if difference > 0 else "red" if difference < 0 else "black"
        ax.text(0.5, 1.05, f"Predicted: {predicted_price:.2f} Ex",
                ha="center", va="center", fontsize=12, color=color,
                transform=ax.transAxes)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return buf


# ────────────────────────────────────────────────────────────────────────
# 3 ▸ bucket-confidence plot  (unchanged)
# ────────────────────────────────────────────────────────────────────────
_BUCKET_COLOURS = {"low": "#E74C3C", "medium": "#F39C12", "high": "#27AE60"}


def generate_bucket_confidence_plot(
    *,
    pred_median: float,
    intervals:   Mapping[str, Tuple[float | None, float | None]],
    bucket_label: str,
    width:  float = DEFAULT_IMG_WIDTH_INCHES,
    height: float = DEFAULT_IMG_HEIGHT_INCHES,
    dpi: int = 96,
) -> io.BytesIO:
    """
    Horizontal 80 % confidence bars + ▼ predicted median.

    • Bars are colour-keyed (Low/Medium/High) and carry a legend so the meaning
      of the palette is obvious.
    • x-limits now expand to fit all intervals + 10 % margin, so nothing clips.
    """
    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi, facecolor="white")
    y_pos = {"high": 0, "medium": 1, "low": 2}

    lo_vals, hi_vals = [], []
    legend_handles   = []

    for key, (lo, hi) in intervals.items():
        if lo is None or hi is None:
            continue
        col = _BUCKET_COLOURS[key]
        ypos = y_pos[key]
        ax.fill_betweenx([ypos - 0.35, ypos + 0.35],
                         lo, hi, color=col, alpha=0.15, zorder=0)
        lw = 6 if key == bucket_label.lower() else 3
        ax.hlines(ypos, lo, hi, color=col, linewidth=lw)
        ax.plot([lo, hi], [ypos] * 2, linestyle="None",
                marker="|", markersize=10, color=col)

        lo_vals.append(lo)
        hi_vals.append(hi)
        legend_handles.append(mpatches.Patch(color=col, label=key.capitalize()))

    # ▼ predicted median
    ax.plot(pred_median, y_pos.get(bucket_label.lower(), 1),
            marker="v", color="black", markersize=9, zorder=5,
            label="Predicted Median")

    # legend: first palette blocks, then the median marker
    handles = legend_handles + [mpatches.Patch(color="black", label="Predicted Median")]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=8)

    # axis cosmetics
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["High", "Medium", "Low"], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Exalts", fontsize=9)
    ax.set_title("80% Confidence Intervals", fontsize=10, fontweight="bold")
    ax.grid(False)

    # dynamic x-range with 10 % padding
    if lo_vals and hi_vals:
        lo_min = max(0, min(lo_vals) * 0.9)
        hi_max = max(hi_vals) * 1.1
        ax.set_xlim(lo_min, hi_max)
    else:
        ax.set_xlim(left=max(0, pred_median * 0.3))

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf
