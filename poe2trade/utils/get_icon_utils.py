import os
import json
import random
import requests

from typing import List, Tuple, Dict
from poe2trade import poe2trade_root, jewel_list

# ----------- Configuration ----------
TARGET_DIR = f"{poe2trade_root}/db/files"
OUTPUT_PATH = f"{poe2trade_root}/db/files/base_images.json"
IMAGE_OUTPUT_ROOT = f"{poe2trade_root}/db/base_icons"
SUBDIR_NAMES = [
    "Body_Armour",
    "Boots",
    "Gloves",
    "Helmet",
    "Focus",
    "Shield",
    "Buckler",
    "Ring",
    "Amulet",
    "Belt",
    "Wand",
    "Quiver",
] + jewel_list
# ------------------------------------

def find_json_files(base_path: str, subdirs: list) -> List[Tuple[str, str]]:
    json_files = []
    for subdir in subdirs:
        full_path = os.path.join(base_path, subdir)
        if os.path.isdir(full_path):
            for root, _, files in os.walk(full_path):
                for file in files:
                    if file.endswith(".json"):
                        full_file_path = os.path.join(root, file)
                        print(f"[FOUND] JSON file: {full_file_path}")
                        json_files.append((full_file_path, subdir))
    return json_files

def extract_unique_items(json_files: List[Tuple[str, str]]) -> List[Dict[str, str]]:
    unique_items = set()
    results = []
    for file_path, category in json_files:
        print(f"[SCAN] Scanning: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                count = 0
                for item in data:
                    item_data = item.get("item")
                    if item_data:
                        base_type = item_data.get("baseType")
                        icon = item_data.get("icon")
                        if base_type and icon:
                            key = (base_type, icon, category)
                            if key not in unique_items:
                                unique_items.add(key)
                                results.append({
                                    "baseType": base_type,
                                    "icon": icon,
                                    "category": category
                                })
                                count += 1
                print(f"[SUCCESS] Extracted {count} items from {file_path}")
        except Exception as e:
            print(f"[ERROR] Failed reading {file_path}: {e}")
    return results

def save_to_json(data: List[Dict[str, str]], output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[DONE] Saved {len(data)} unique entries to {output_path}")

def sanitize_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).rstrip()

def download_images(data: List[Dict[str, str]], output_root: str):
    print("[INFO] Starting image downloads...")
    for entry in data:
        base_type = entry["baseType"]
        icon_url = entry["icon"]
        category = entry["category"]

        safe_base_type = sanitize_filename(base_type)
        category_path = os.path.join(output_root, category)
        os.makedirs(category_path, exist_ok=True)

        image_path = os.path.join(category_path, f"{safe_base_type}.png")

        if os.path.exists(image_path):
            print(f"[SKIP] Already exists: {image_path}")
            continue

        try:
            response = requests.get(icon_url, timeout=10)
            if response.status_code == 200:
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                print(f"[DOWNLOADED] {image_path}")
            else:
                print(f"[ERROR] Failed to download {icon_url}: Status {response.status_code}")
        except Exception as e:
            print(f"[ERROR] Exception downloading {icon_url}: {e}")

def assign_default_icons(output_root: str, subdirs: list):
    print("[INFO] Assigning default icons...")
    for category in subdirs:
        category_path = os.path.join(output_root, category)
        if not os.path.isdir(category_path):
            print(f"[WARN] No folder found for {category}, skipping.")
            continue

        png_files = [f for f in os.listdir(category_path) if f.endswith(".png") and f != "default.png"]
        if not png_files:
            print(f"[WARN] No PNG files found in {category_path}, skipping.")
            continue

        chosen_file = random.choice(png_files)
        default_path = os.path.join(category_path, "default.png")
        chosen_path = os.path.join(category_path, chosen_file)

        # Copy content into default.png
        with open(chosen_path, "rb") as src, open(default_path, "wb") as dst:
            dst.write(src.read())

        print(f"[DEFAULT] Assigned {chosen_file} as default for {category}")

def main():
    print(f"[INFO] Starting scan in: {TARGET_DIR}")
    json_files = find_json_files(TARGET_DIR, SUBDIR_NAMES)
    print(f"[INFO] Found {len(json_files)} JSON files to process.")
    unique_data = extract_unique_items(json_files)
    save_to_json(unique_data, OUTPUT_PATH)
    download_images(unique_data, IMAGE_OUTPUT_ROOT)
    assign_default_icons(IMAGE_OUTPUT_ROOT, SUBDIR_NAMES)

if __name__ == "__main__":
    main()
