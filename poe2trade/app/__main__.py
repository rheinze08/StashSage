"""
__main__.py · Unified launcher for StashSage
────────────────────────────────────────────
• Loads config from disk
• Starts background services (Flask + Discord bot)
• Launches the Tkinter GUI in the main thread
"""

from poe2trade.app.config_manager import load_config
from poe2trade.app.discord_flask import start_services
from poe2trade.app.gui_tk import run_tkinter_app


def main() -> None:
    # 1 ) load persisted JSON config
    cfg = load_config()

    # 2 ) spawn Flask server, scraper loop, and Discord client (non-blocking)
    start_services(cfg)
    print("✅ Discord / Flask services started.")

    # 3 ) run the Tk GUI (blocks until user closes window)
    run_tkinter_app(cfg)


if __name__ == "__main__":
    main()
