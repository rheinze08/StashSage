import threading
from poe2trade.app.gui_tk import run_tkinter_app
from poe2trade.app.discord_flask import run_discord_flask_app, init_log_files_from_config
from poe2trade.app.config_manager import load_config

def main():
    config = load_config()
    init_log_files_from_config(config)

    tkinter_thread = threading.Thread(target=run_tkinter_app, args=(config,), daemon=True)
    tkinter_thread.start()
    print("✅ Tkinter GUI started.")

    if config.get("discord_user_id", "").strip().isdigit():
        discord_thread = threading.Thread(target=run_discord_flask_app, args=(config,), daemon=True)
        discord_thread.start()
        print("✅ Discord bot started.")
    else:
        print("⚠️ No valid Discord ID found. Discord bot not started.")

    tkinter_thread.join()

if __name__ == "__main__":
    main()
