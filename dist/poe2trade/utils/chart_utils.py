"""
chart_utils.py  ·  helper plots for price history, offers table and prediction
-----------------------------------------------------------------------------

Every public helper returns an in‑memory PNG (`io.BytesIO`) that can be pushed
directly to an overlay or Discord bot.

    • generate_price_chart_for_item()      ←  now shows mean / median / range
    • generate_offers_table_chart()
    • generate_prediction_frequency_plot() ←  horizontal, sorted, no legend
"""

import io
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np

DEFAULT_IMG_WIDTH_INCHES = 4
DEFAULT_IMG_HEIGHT_INCHES = 3

# ═══════════════════════════════════════════════════════════════════════════
# 1. Historical price line chart
# ═══════════════════════════════════════════════════════════════════════════
def generate_price_chart_for_item(
    item_name,
    df_trades,
    item_col: str = "item_name",
    predicted_mean: float | None = None,
    predicted_median: float | None = None,
    predicted_min: float | None = None,
    predicted_max: float | None = None,
    width: float = DEFAULT_IMG_WIDTH_INCHES,
    height: float = DEFAULT_IMG_HEIGHT_INCHES,
):
    """
    Line plot of Exalted / Divine offers for an item.
    A second line under the title shows mean / median / range when supplied.
    Always returns a PNG buffer (even on empty data).
    """
    fig, ax1 = plt.subplots(figsize=(width, height), facecolor="white")
    ax2 = None

    if df_trades.empty:
        ax1.text(0.5, 0.5, "No trade history",
                 ha="center", va="center", fontsize=12)
        ax1.set_title(f"Offer History for {item_name}",
                      fontsize=10, fontweight="bold")
    else:
        df_item = df_trades[
            df_trades[item_col].str.replace(",", "").str.lower()
            == item_name.replace(",", "").lower()
        ].copy()

        if df_item.empty:
            ax1.text(0.5, 0.5, "No trade history for this item",
                     ha="center", va="center", fontsize=12)
            ax1.set_title(f"Offer History for {item_name}",
                          fontsize=10, fontweight="bold")
        else:
            df_item.sort_values("timestamp", inplace=True)
            df_item["currency"] = df_item["currency"].str.lower()

            df_ex  = df_item[df_item["currency"] == "exalted"].copy()
            df_div = df_item[df_item["currency"] == "divine"].copy()
            for d in (df_item, df_ex, df_div):
                d["x_date"] = d["timestamp"].dt.floor("D")

            line_ex = line_div = None
            ax1.set_title(f"Offer History for {item_name}",
                          fontsize=10, fontweight="bold")

            if not df_ex.empty:
                line_ex = ax1.plot(
                    df_ex["x_date"], df_ex["amount"],
                    marker="o", linestyle="-", label="Exalted", color="blue"
                )
                ax1.set_ylabel("Exalted price", fontsize=8)

            if not df_div.empty:
                ax2 = ax1.twinx()
                line_div = ax2.plot(
                    df_div["x_date"], df_div["amount"],
                    marker="s", linestyle="--", label="Divine", color="red"
                )
                ax2.set_ylabel("Divine price", fontsize=8)

            if line_ex or line_div:
                lines, labels = [], []
                if line_ex: lines += line_ex; labels.append("Exalted")
                if line_div: lines += line_div; labels.append("Divine")
                fig.legend(lines, labels, loc="lower center", ncol=2,
                           fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.05))

            x_dates = sorted(df_item["x_date"].unique())
            ax1.set_xticks(x_dates)
            ax1.set_xticklabels([d.strftime("%m-%d") for d in x_dates],
                                rotation=90, fontsize=7, ha="center")
            ax1.set_xlabel("")

    # second‑line title with prediction stats
    if all(v is not None for v in (predicted_mean, predicted_median,
                                   predicted_min, predicted_max)):
        t1 = ax1.get_title()
        t2 = (f"Mean: {predicted_mean:.0f}   "
              f"Median: {predicted_median:.0f}   "
              f"Range: {predicted_min:.0f}-{predicted_max:.0f}")
        ax1.set_title(f"{t1}\n{t2}", fontsize=10, fontweight="bold")

    ax1.grid(False)
    if ax2: ax2.grid(False)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.2)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf

# ═══════════════════════════════════════════════════════════════════════════
# 2. Last‑offers table
# ═══════════════════════════════════════════════════════════════════════════
def generate_offers_table_chart(
    item_name,
    df_trades,
    item_col: str = "item_name",
    predicted_price: float | None = None,
    difference: float = 0.0,
    width: float = DEFAULT_IMG_WIDTH_INCHES,
    height: float = DEFAULT_IMG_HEIGHT_INCHES,
    show_legacy_text: bool = False,
):
    """
    PNG containing the last five offers table only.
    Prediction text is suppressed by default (handled in the prediction plot).
    """
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_axis_off()

    if df_trades.empty:
        ax.text(0.5, 0.5, "No trade history",
                ha="center", va="center", fontsize=12)
        plt.title(f"Last 5 Offers for {item_name}",
                  fontsize=12, fontweight="bold", pad=15)
    else:
        df_item = df_trades[
            df_trades[item_col].str.replace(",", "").str.lower()
            == item_name.replace(",", "").lower()
        ].copy()

        if df_item.empty:
            ax.text(0.5, 0.5, "No trade offers for this item",
                    ha="center", va="center", fontsize=12)
            plt.title(f"Last 5 Offers for {item_name}",
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
                    colColours=["#dddddd"]*3,
                )
                for _, c in tbl.get_celld().items():
                    c.set_linewidth(1); c.set_edgecolor("black")
                tbl.auto_set_font_size(False); tbl.set_fontsize(10); tbl.scale(1,1.4)

            plt.title(f"Last 5 Offers for {item_name}",
                      fontsize=12, fontweight="bold", pad=15)

    if show_legacy_text and predicted_price is not None:
        color = "green" if difference>0 else "red" if difference<0 else "black"
        ax.text(0.5, 1.05, f"Predicted: {predicted_price:.2f} Ex",
                ha="center", va="center", fontsize=12, color=color,
                transform=ax.transAxes)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf

# ═══════════════════════════════════════════════════════════════════════════
# 3. Prediction frequency plot (horizontal, sorted, no legend/grid/text)
# ═══════════════════════════════════════════════════════════════════════════
def generate_prediction_frequency_plot(
    predictions,
    title: str = "Prediction",
    width: float = DEFAULT_IMG_WIDTH_INCHES,
    height: float = DEFAULT_IMG_HEIGHT_INCHES,
    dpi: int = 100,
):
    items = list(predictions.items()) if isinstance(predictions, dict) else list(predictions)
    items.sort(key=lambda kv: kv[1])
    names, vals = zip(*items)

    vals = np.asarray(vals, float)
    q1, q3 = np.percentile(vals, [25, 75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5*iqr, q3 + 1.5*iqr
    colours = ["tab:red" if (v < lo or v > hi) else "tab:blue" for v in vals]

    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    y = np.arange(len(vals))
    ax.barh(y, vals, color=colours, height=.6)

    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("Exalts", fontsize=8)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.grid(False)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf
