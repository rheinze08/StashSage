"""
gui_tk.py  ·  overlay front‑end for StashSage / Path of Exile II
"""

import io, os, subprocess, sys, time, tkinter as tk
from pathlib import Path
from tkinter import messagebox
from statistics import median

import keyboard, pandas as pd, pyperclip
from PIL import Image, ImageTk

from poe2trade.app import config_manager, submodule_path
from poe2trade.utils.log_utils import read_all_log_trades
from poe2trade.utils.chart_utils import (
    generate_price_chart_for_item,
    generate_offers_table_chart,
    generate_prediction_frequency_plot,
)
from poe2trade.utils.gui_utils import predict_item_text

IMG_WIDTH_INCHES, IMG_HEIGHT_INCHES = 4, 3
LOG_FILES: list[str] = []
current_overlay: tk.Toplevel | None = None
steam_entry = ggg_entry = discord_user_id_entry = discord_bot_token_entry = None
global_gui_config = {}
client_day_filter = 30


# ── config helpers ───────────────────────────────────────────────────────────
def save_gui_config():
    config_manager.save_config({
        "poe_account": "",
        "steam_client_log_dir": steam_entry.get(),
        "ggg_client_log_dir":   ggg_entry.get(),
        "discord_user_id":      discord_user_id_entry.get(),
        "discord_bot_token":    discord_bot_token_entry.get(),
    })


def save_config_and_restart():
    save_gui_config()
    os.execl(sys.executable, sys.executable, *sys.argv)


# ── overlay ------------------------------------------------------------------
def show_overlay(item_name, price_buf, freq_buf, table_buf,
                 predicted_price=None, debug_info=None):
    global current_overlay
    if current_overlay is not None:
        try: current_overlay.destroy()
        except Exception: pass

    ov = tk.Toplevel()
    current_overlay = ov
    ov.title(item_name)
    ov.lift(); ov.attributes("-topmost", True)
    ov.after_idle(lambda: ov.attributes("-topmost", False))

    any_img = False
    def add(buf: io.BytesIO):
        nonlocal any_img
        try:
            pil = Image.open(buf)
            tk_img = ImageTk.PhotoImage(pil)
            lbl = tk.Label(ov, image=tk_img)
            lbl.image = tk_img
            lbl.pack()
            any_img = True
        except Exception as e:
            print("[overlay-img-err]", e)

    if price_buf: add(price_buf)   # 1
    if freq_buf:  add(freq_buf)    # 2
    if table_buf: add(table_buf)   # 3

    if not any_img:
        tk.Label(ov, text=f"No trade history for {item_name}").pack()

    if predicted_price is not None or debug_info:
        fr = tk.Frame(ov); fr.pack(pady=5, fill="both", expand=True)
        tk.Label(fr, text="Debug Info:", font=("Courier",10,"bold"),
                 anchor="w").pack(fill="x")
        txt = tk.Text(fr, height=10, wrap="word", font=("Courier",8))
        if predicted_price is not None:
            txt.insert("end", f"Predicted Price → {predicted_price:.2f} Ex\n\n")
        if debug_info:
            txt.insert("end", debug_info)
        txt.config(state="disabled"); txt.pack(fill="both", expand=True)

    ov.update_idletasks()
    sw, sh = ov.winfo_screenwidth(), ov.winfo_screenheight()
    ov.geometry(f"{ov.winfo_width()}x{ov.winfo_height()}+{(sw-ov.winfo_width())//2}+{(sh-ov.winfo_height())//2}")


# ── log helpers --------------------------------------------------------------
def scrape_log_trades() -> pd.DataFrame:
    trades = read_all_log_trades(LOG_FILES)
    if not trades:
        return pd.DataFrame(columns=["timestamp","buyer","item_name","amount","currency"])
    df = pd.DataFrame(trades)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=client_day_filter)
    return df[df["timestamp"] >= cutoff].sort_values("timestamp")


def parse_item_name(txt: str) -> str | None:
    out, cap = [], False
    for ln in txt.splitlines():
        if ln.startswith("Rarity:") and "rare" in ln.lower():
            cap = True; continue
        if cap:
            if ln.strip().startswith("--------"): break
            out.append(ln.strip())
    return " ".join(out) if out else None


# ── hot‑key ------------------------------------------------------------------
def on_hotkey():
    keyboard.press_and_release("ctrl+c"); time.sleep(0.2)
    clip = pyperclip.paste()

    ml = predict_item_text(clip) or {}
    pred_avg = ml.get("average")
    pred_min = ml.get("min")
    pred_max = ml.get("max")
    model_preds = (ml.get("model_predictions") or ml.get("per_model") or
                   ml.get("predictions") or ml.get("models") or {})
    pred_med = median(model_preds.values()) if model_preds else None
    actual   = ml.get("actual")

    debug = ""
    if all(v is not None for v in (pred_min, pred_max, pred_avg, pred_med)):
        debug += (f"Min: {pred_min:.2f}, Max: {pred_max:.2f}, "
                  f"Avg: {pred_avg:.2f}, Med: {pred_med:.2f}\n")
    if actual is not None and pred_avg is not None:
        debug += f"Actual → {actual:.2f}\nDiff → {pred_avg-actual:+.2f}\n"

    item_name = parse_item_name(clip) or "Unknown Item"
    trades_df = scrape_log_trades()

    price_buf = generate_price_chart_for_item(item_name, trades_df)

    freq_title = "Prediction"
    if all(v is not None for v in (pred_avg, pred_med, pred_min, pred_max)):
        freq_title = (f"Prediction  (Mean {pred_avg:.0f}  "
                      f"Median {pred_med:.0f}  "
                      f"Range {pred_min:.0f}-{pred_max:.0f})")

    freq_buf = None
    if model_preds:
        freq_buf = generate_prediction_frequency_plot(
            model_preds,
            title=freq_title,
            width=IMG_WIDTH_INCHES, height=IMG_HEIGHT_INCHES)

    table_buf = generate_offers_table_chart(item_name, trades_df)

    show_overlay(item_name, price_buf, freq_buf, table_buf, pred_avg, debug)


def setup_hotkeys():
    keyboard.add_hotkey("ctrl+q", on_hotkey)


# ── workflow buttons ---------------------------------------------------------
def build_workflow():
    if not (steam_entry.get().strip() and ggg_entry.get().strip()):
        messagebox.showerror("Error", "Need Steam + GGG log locations."); return
    messagebox.showinfo("Info", "Building stash report…")
    save_gui_config()
    from poe2trade.utils.scrape_utils import scrape_trade
    scrape_trade(
        {"Listed":"Up to 1 Month","Seller Account":global_gui_config.get("poe_account","")},
        os.path.join(submodule_path, "files", "stash_report.xlsx")
    )
    messagebox.showinfo("Done", "Stash report built! Click 'Display Stash Report'.")


def display_excel():
    xl = Path(submodule_path) / "files" / "stash_report.xlsx"
    if not xl.exists():
        messagebox.showerror("Error", "stash_report.xlsx not found."); return
    os.startfile(xl) if os.name == "nt" else subprocess.run(["open", str(xl)])


# ── Tk helpers ---------------------------------------------------------------
def create_labeled_entry(parent, label, default=""):
    tk.Label(parent, text=label).pack(anchor="w", padx=10, pady=2)
    var = tk.StringVar(value=default)
    ent = tk.Entry(parent, textvariable=var)
    ent.pack(fill="x", padx=10, pady=2, expand=True)
    return ent


def run_tkinter_app(cfg=None):
    global steam_entry, ggg_entry, discord_user_id_entry, discord_bot_token_entry, global_gui_config
    global_gui_config = cfg or {}

    root = tk.Tk()
    root.title("StashSage for POE 2  (Budodude)")
    root.geometry("500x400")

    steam_entry  = create_labeled_entry(root, "Steam Logs Location",  global_gui_config.get("steam_client_log_dir",""))
    ggg_entry    = create_labeled_entry(root, "GGG   Logs Location",  global_gui_config.get("ggg_client_log_dir",""))
    discord_user_id_entry  = create_labeled_entry(root, "Discord User ID",  global_gui_config.get("discord_user_id",""))
    discord_bot_token_entry = create_labeled_entry(root, "Discord Bot Token", global_gui_config.get("discord_bot_token",""))

    tk.Button(root, text="Save Config & Restart", command=save_config_and_restart).pack(pady=5)
    tk.Button(root, text="Build Stash Report",     command=build_workflow).pack(pady=5)
    tk.Button(root, text="Display Stash Report",   command=display_excel).pack(pady=5)

    setup_hotkeys()

    LOG_FILES.clear()
    if (p := global_gui_config.get("steam_client_log_dir","").strip()): LOG_FILES.append(p)
    if (p := global_gui_config.get("ggg_client_log_dir","").strip()):   LOG_FILES.append(p)

    root.mainloop()
