from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    _MPL = True
except Exception:
    _MPL = False


_SEGMENTS = {
    "ar_only", "ev_only", "es_only",
    "ar_ev_only", "ar_es_only", "ev_es_only", "all_three",
}
_BUCKET_COLORS = {"Low": "#E74C3C", "Medium": "#F39C12", "High": "#27AE60"}
_TRIMMED_MAE_COVERAGES = (100, 90, 80, 70, 60, 50)
_TRIMMED_COHORTS = ("Total", "Low", "Medium", "High")


def _parse_scoring_stem(stem: str) -> Tuple[str, Optional[str]]:
    if not stem.endswith("_scoring"):
        return stem, None
    name = stem[: -len("_scoring")]
    for seg in sorted(_SEGMENTS, key=len, reverse=True):
        if name.endswith(f"_{seg}"):
            return name[: -len(f"_{seg}")], seg
    return name, None


def _compute_metrics(actual: np.ndarray, predicted: np.ndarray) -> Dict:
    mask = np.isfinite(actual) & np.isfinite(predicted) & (actual > 0) & (predicted > 0)
    a, p = actual[mask], predicted[mask]
    n = len(a)
    if n == 0:
        return {"n": 0, "mae": None, "mape": None, "r2": None}
    mae = float(np.mean(np.abs(a - p)))
    mape = float(np.mean(np.abs((a - p) / a)) * 100)
    ss_res = float(np.sum((a - p) ** 2))
    ss_tot = float(np.sum((a - np.mean(a)) ** 2))
    r2 = (1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return {"n": n, "mae": mae, "mape": mape, "r2": r2}


def _compute_trimmed_mae(
    actual: np.ndarray,
    predicted: np.ndarray,
    coverages: Tuple[int, ...] = _TRIMMED_MAE_COVERAGES,
) -> Dict[int, Dict[str, Optional[float]]]:
    mask = np.isfinite(actual) & np.isfinite(predicted) & (actual > 0) & (predicted > 0)
    a, p = actual[mask], predicted[mask]
    n = len(a)
    out: Dict[int, Dict[str, Optional[float]]] = {}
    if n == 0:
        for cov in coverages:
            out[cov] = {"n": 0, "mae": None}
        return out

    abs_error = np.sort(np.abs(a - p))
    for cov in coverages:
        keep_n = int(np.ceil(n * (cov / 100.0)))
        keep_n = max(1, min(n, keep_n))
        out[cov] = {"n": keep_n, "mae": float(np.mean(abs_error[:keep_n]))}
    return out


def _compute_trimmed_mae_by_bucket(df: pd.DataFrame) -> Dict[str, Dict[int, Dict[str, Optional[float]]]]:
    actual = pd.to_numeric(df.get("price", pd.Series(dtype=float)), errors="coerce")
    predicted = pd.to_numeric(df.get("pred_median", pd.Series(dtype=float)), errors="coerce")

    result: Dict[str, Dict[int, Dict[str, Optional[float]]]] = {
        "Total": _compute_trimmed_mae(actual.to_numpy(), predicted.to_numpy())
    }
    if "bucket_label" not in df.columns:
        return result

    for lbl in ("Low", "Medium", "High"):
        sel = df["bucket_label"] == lbl
        result[lbl] = _compute_trimmed_mae(actual[sel].to_numpy(), predicted[sel].to_numpy())
    return result


def _fmt(v, spec=".2f"):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    return format(v, spec)


def _summary_page(pdf: "PdfPages", category: str, segments: List[Dict]) -> None:
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(11, max(6.0, 2.2 + len(segments) * 0.9)),
        gridspec_kw={"height_ratios": [1.0, 1.1]},
    )
    ax, trimmed_ax = axes
    ax.axis("off")
    trimmed_ax.axis("off")

    rows = []
    total_n = 0
    mae_vals: List[float] = []
    mape_vals: List[float] = []
    r2_vals: List[float] = []

    for s in segments:
        m = s["metrics"]
        label = s["segment"] or "global"
        rows.append([
            label,
            str(m["n"]),
            _fmt(m["mae"]),
            (_fmt(m["mape"]) + "%") if m["mape"] is not None else "—",
            _fmt(m["r2"]),
        ])
        total_n += m["n"]
        if m["mae"] is not None:
            mae_vals.append(m["mae"])
        if m["mape"] is not None:
            mape_vals.append(m["mape"])
        if m["r2"] is not None:
            r2_vals.append(m["r2"])

    avg_mae = np.mean(mae_vals) if mae_vals else None
    avg_mape = np.mean(mape_vals) if mape_vals else None
    avg_r2 = np.mean(r2_vals) if r2_vals else None
    rows.append([
        "TOTAL / AVG",
        str(total_n),
        _fmt(avg_mae),
        (_fmt(avg_mape) + "%") if avg_mape is not None else "—",
        _fmt(avg_r2),
    ])

    col_labels = ["Segment", "Samples", "MAE", "MAPE", "R²"]
    table = ax.table(cellText=rows, colLabels=col_labels, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.4, 1.8)

    n_cols = len(col_labels)
    for j in range(n_cols):
        table[0, j].set_facecolor("#2C3E50")
        table[0, j].set_text_props(color="white", fontweight="bold")

    total_row_idx = len(rows)
    for j in range(n_cols):
        table[total_row_idx, j].set_facecolor("#D5DBDB")
        table[total_row_idx, j].set_text_props(fontweight="bold")

    for i in range(1, len(rows)):
        color = "#F2F3F4" if i % 2 == 0 else "white"
        if i < total_row_idx:
            for j in range(n_cols):
                table[i, j].set_facecolor(color)

    trimmed_rows = []
    all_actual: List[np.ndarray] = []
    all_predicted: List[np.ndarray] = []
    for s in segments:
        label = s["segment"] or "global"
        trimmed = s.get("trimmed_mae", {})
        row = [label, str(trimmed.get(100, {}).get("n", 0))]
        for cov in _TRIMMED_MAE_COVERAGES:
            val = trimmed.get(cov, {}).get("mae")
            row.append(_fmt(val))
        trimmed_rows.append(row)
        seg_df = s.get("df")
        if isinstance(seg_df, pd.DataFrame):
            all_actual.append(pd.to_numeric(seg_df.get("price", pd.Series(dtype=float)), errors="coerce").to_numpy())
            all_predicted.append(
                pd.to_numeric(seg_df.get("pred_median", pd.Series(dtype=float)), errors="coerce").to_numpy()
            )

    if all_actual and all_predicted:
        category_trimmed = _compute_trimmed_mae(np.concatenate(all_actual), np.concatenate(all_predicted))
    else:
        category_trimmed = _compute_trimmed_mae(np.array([]), np.array([]))
    total_row = ["CATEGORY TOTAL", str(category_trimmed.get(100, {}).get("n", 0))]
    for cov in _TRIMMED_MAE_COVERAGES:
        total_row.append(_fmt(category_trimmed.get(cov, {}).get("mae")))
    trimmed_rows.append(total_row)

    trimmed_col_labels = ["Segment", "Valid N"] + [f"MAE@{cov}" for cov in _TRIMMED_MAE_COVERAGES]
    trimmed_table = trimmed_ax.table(
        cellText=trimmed_rows,
        colLabels=trimmed_col_labels,
        loc="center",
        cellLoc="center",
    )
    trimmed_table.auto_set_font_size(False)
    trimmed_table.set_fontsize(8)
    trimmed_table.scale(1.15, 1.5)

    trimmed_n_cols = len(trimmed_col_labels)
    for j in range(trimmed_n_cols):
        trimmed_table[0, j].set_facecolor("#2C3E50")
        trimmed_table[0, j].set_text_props(color="white", fontweight="bold")

    trimmed_total_row_idx = len(trimmed_rows)
    for j in range(trimmed_n_cols):
        trimmed_table[trimmed_total_row_idx, j].set_facecolor("#D5DBDB")
        trimmed_table[trimmed_total_row_idx, j].set_text_props(fontweight="bold")

    for i in range(1, len(trimmed_rows)):
        color = "#F2F3F4" if i % 2 == 0 else "white"
        if i < trimmed_total_row_idx:
            for j in range(trimmed_n_cols):
                trimmed_table[i, j].set_facecolor(color)

    cat_title = category.replace("_", " ").title()
    fig.suptitle(f"Category: {cat_title}", fontsize=14, fontweight="bold", y=0.98)
    ax.set_title("Scoring Summary  —  Predicted vs Actual Accuracy", fontsize=9, pad=8)

    trimmed_ax.set_title(
        "Trimmed MAE by Best-Covered Items (Total Cohort)",
        fontsize=9,
        pad=8,
    )

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _trimmed_mae_page(
    pdf: "PdfPages",
    category: str,
    segment: Optional[str],
    df: pd.DataFrame,
) -> None:
    by_bucket = _compute_trimmed_mae_by_bucket(df)
    if not by_bucket:
        return

    rows = []
    for cohort in _TRIMMED_COHORTS:
        if cohort not in by_bucket:
            continue
        trimmed = by_bucket[cohort]
        valid_n = trimmed.get(100, {}).get("n", 0)
        row = [cohort, str(valid_n)]
        for cov in _TRIMMED_MAE_COVERAGES:
            row.append(_fmt(trimmed.get(cov, {}).get("mae")))
        rows.append(row)

    if not rows:
        return

    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.axis("off")

    col_labels = ["Cohort", "Valid N"] + [f"MAE@{cov}" for cov in _TRIMMED_MAE_COVERAGES]
    table = ax.table(cellText=rows, colLabels=col_labels, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.7)

    n_cols = len(col_labels)
    for j in range(n_cols):
        table[0, j].set_facecolor("#2C3E50")
        table[0, j].set_text_props(color="white", fontweight="bold")

    for i, row in enumerate(rows, start=1):
        color = "#F2F3F4" if i % 2 == 0 else "white"
        for j in range(n_cols):
            table[i, j].set_facecolor(color)
        if row[0] in _BUCKET_COLORS:
            table[i, 0].set_facecolor(_BUCKET_COLORS[row[0]])
            table[i, 0].set_text_props(color="white", fontweight="bold")
        if row[0] == "Total":
            for j in range(n_cols):
                table[i, j].set_text_props(fontweight="bold")

    seg_label = segment or "global"
    cat_title = category.replace("_", " ").title()
    fig.suptitle(
        f"{cat_title} - {seg_label}: Trimmed MAE by Bucket",
        fontsize=13,
        fontweight="bold",
        y=0.96,
    )
    ax.set_title(
        "Each MAE@coverage keeps the lowest absolute-error rows within that cohort.",
        fontsize=8,
        pad=8,
    )

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _distribution_page(
    pdf: "PdfPages",
    category: str,
    segment: Optional[str],
    df: pd.DataFrame,
    bins: int = 30,
) -> None:
    pred_col = pd.to_numeric(df.get("pred_median", pd.Series(dtype=float)), errors="coerce")
    all_pred = pred_col.dropna().to_numpy()
    if all_pred.size < 2:
        return

    buckets = ("Low", "Medium", "High")
    colours = {"Low": "#E74C3C", "Medium": "#F39C12", "High": "#27AE60"}

    p_lo, p_hi = (
        np.percentile(all_pred, [1, 99]) if all_pred.size >= 10
        else (float(all_pred.min()), float(all_pred.max()))
    )
    if not np.isfinite(p_lo) or not np.isfinite(p_hi) or p_lo == p_hi:
        p_lo, p_hi = float(all_pred.min()), float(all_pred.max()) + 1e-9
    edges = np.linspace(p_lo, p_hi, max(5, bins + 1))

    fig, ax = plt.subplots(figsize=(10, 5))

    has_buckets = "bucket_label" in df.columns
    plotted = False
    for lbl in buckets:
        if has_buckets:
            vals = pred_col[df["bucket_label"] == lbl].dropna().to_numpy()
        else:
            vals = np.array([])
        if len(vals):
            counts, _ = np.histogram(vals, bins=edges)
            widths = np.diff(edges)
            ax.bar(
                edges[:-1], counts, width=widths, align="edge",
                color=colours[lbl], alpha=0.28, edgecolor="none",
                label=f"{lbl} ({len(vals)})",
            )
            ax.step(edges, np.r_[counts, counts[-1]], where="post",
                    color=colours[lbl], linewidth=1.8)
            plotted = True

    if not plotted:
        counts, _ = np.histogram(all_pred, bins=edges)
        widths = np.diff(edges)
        ax.bar(edges[:-1], counts, width=widths, align="edge",
               color="#3498DB", alpha=0.4, edgecolor="none", label="All")

    ax.set_xlim(p_lo, p_hi)
    ax.set_xlabel("Predicted Price (exalts)")
    ax.set_ylabel("Items")
    ax.legend(fontsize=8, loc="upper right")

    seg_label = segment or "global"
    cat_title = category.replace("_", " ").title()
    ax.set_title(
        f"{cat_title} — {seg_label}:  Score Distribution (Low / Medium / High)",
        fontsize=11, fontweight="bold",
    )

    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _scatter_page(
    pdf: "PdfPages",
    category: str,
    segment: Optional[str],
    df: pd.DataFrame,
) -> None:
    actual = pd.to_numeric(df.get("price", pd.Series(dtype=float)), errors="coerce")
    predicted = pd.to_numeric(df.get("pred_median", pd.Series(dtype=float)), errors="coerce")
    mask = actual.notna() & predicted.notna() & (actual > 0) & (predicted > 0)
    a = actual[mask].to_numpy()
    p = predicted[mask].to_numpy()

    if len(a) < 2:
        return

    fig, ax = plt.subplots(figsize=(8, 6))

    use_log = (a.max() / max(float(a.min()), 1e-9)) > 50

    if "bucket_label" in df.columns:
        buckets = df.loc[mask, "bucket_label"].values
        for lbl, color in _BUCKET_COLORS.items():
            sel = buckets == lbl
            if sel.any():
                ax.scatter(a[sel], p[sel], c=color, label=lbl, alpha=0.45, s=18, edgecolors="none")
    else:
        ax.scatter(a, p, alpha=0.4, s=18, color="#3498DB", edgecolors="none")

    lo = min(float(a.min()), float(p.min()))
    hi = max(float(a.max()), float(p.max()))
    ax.plot([lo, hi], [lo, hi], "k--", linewidth=1.2, alpha=0.55, label="y = x")

    if use_log:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Actual Price (log scale)")
        ax.set_ylabel("Predicted Price (log scale)")
    else:
        ax.set_xlabel("Actual Price")
        ax.set_ylabel("Predicted Price")

    m = _compute_metrics(a, p)
    ann = f"n={m['n']}   MAE={_fmt(m['mae'])}   MAPE={_fmt(m['mape'])}%   R²={_fmt(m['r2'])}"
    ax.text(
        0.03, 0.97, ann,
        transform=ax.transAxes, fontsize=8, verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", alpha=0.85),
    )

    seg_label = segment or "global"
    cat_title = category.replace("_", " ").title()
    ax.set_title(f"{cat_title} — {seg_label}:  Predicted vs Actual", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="lower right")

    fig.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _scoring_sources(output_dir: Path) -> List[Path]:
    json_files = sorted(output_dir.glob("*_scoring.json"))
    if json_files:
        return json_files
    return sorted(output_dir.glob("*_scoring.xlsx"))


def _read_scoring_source(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as fh:
            rows = json.load(fh)
        return pd.DataFrame(rows)
    return pd.read_excel(path)


def generate_score_super_report(output_dir: Path) -> Optional[Path]:
    """Read compact scoring sidecars in output_dir and write score_super_report.pdf."""
    if not _MPL:
        print("[REPORT] matplotlib not available; skipping PDF report")
        return None

    scoring_files = _scoring_sources(output_dir)
    if not scoring_files:
        print("[REPORT] no scoring files found; skipping PDF report")
        return None

    grouped: Dict[str, List[Dict]] = {}
    for f in scoring_files:
        category, segment = _parse_scoring_stem(f.stem)
        grouped.setdefault(category, []).append({"segment": segment, "file": f})

    pdf_path = output_dir / "score_super_report.pdf"
    with PdfPages(pdf_path) as pdf:
        for category, entries in sorted(grouped.items()):
            segments_data = []
            for entry in sorted(entries, key=lambda e: (e["segment"] or "")):
                try:
                    df = _read_scoring_source(entry["file"])
                except Exception as exc:
                    print(f"[REPORT] could not read {entry['file'].name}: {exc}")
                    continue
                actual = pd.to_numeric(df.get("price", pd.Series(dtype=float)), errors="coerce").to_numpy()
                predicted = pd.to_numeric(df.get("pred_median", pd.Series(dtype=float)), errors="coerce").to_numpy()
                segments_data.append({
                    "segment": entry["segment"],
                    "df": df,
                    "metrics": _compute_metrics(actual, predicted),
                    "trimmed_mae": _compute_trimmed_mae(actual, predicted),
                })

            if not segments_data:
                continue

            _summary_page(pdf, category, segments_data)
            for seg in segments_data:
                if seg["metrics"]["n"] >= 2:
                    _trimmed_mae_page(pdf, category, seg["segment"], seg["df"])
                    _scatter_page(pdf, category, seg["segment"], seg["df"])
                    _distribution_page(pdf, category, seg["segment"], seg["df"])

    print(f"[REPORT] PDF saved -> {pdf_path}")
    return pdf_path
