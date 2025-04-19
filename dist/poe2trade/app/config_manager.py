import json
import os
import tkinter as tk
from tkinter import messagebox
from poe2trade.app import submodule_path

config_path = os.path.join(submodule_path, "files", "config.json")

# Default log locations
DEFAULT_CONFIG = {
    "poe_account": "",
    "steam_client_log_dir": r"C:\Program Files (x86)\Steam\steamapps\common\Path of Exile 2\logs\client.txt",
    "ggg_client_log_dir": r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile 2\logs\client.txt",
    "discord_user_id": "",
    "discord_bot_token": "",
}

def load_config():
    """Load config from file or create a new one with default values if missing/corrupt."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)

            # Ensure all expected keys are present
            missing_keys = [key for key in DEFAULT_CONFIG if key not in config_data]
            if missing_keys:
                print(f"⚠️ Missing keys in config: {missing_keys}. Updating config with defaults.")
                for key in missing_keys:
                    config_data[key] = DEFAULT_CONFIG[key]
                save_config(config_data)

            print("✅ Config loaded successfully.")
            return config_data

        except json.JSONDecodeError:
            print("⚠️ Corrupt config file detected. Recreating...")
            messagebox.showerror("Error", "Corrupt config file. Deleting it.")
            os.remove(config_path)  # Remove the bad file

    # If the file didn't exist or was corrupt, create a new one
    save_config(DEFAULT_CONFIG)
    print("🆕 No valid config found. Created a new one with defaults.")
    return DEFAULT_CONFIG

def save_config(config_data):
    """Save the provided config data to the config file."""
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=4)
    print("💾 Config updated successfully.")
