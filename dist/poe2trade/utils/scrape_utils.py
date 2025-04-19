def scrape_trade(sub_filters=None, output_path=None, wait_interval=10):
    """
    Scrapes PoE trade data based on sub_filters, and saves the resulting
    items to an Excel file at the exact 'output_path' specified by the caller.

    - You must supply the entire path (including filename). No default naming or folder structure is assumed.
    - If 'output_path' is omitted or None, the data is simply not saved.
    - Added 'wait_interval' (default=10 seconds) to ensure a minimum wait between price interval searches.
    - NEW: If we detect 3 consecutive intervals (price ranges) with zero new items,
      we skip the remaining intervals for that search.

    Example usage:
        scrape_trade(
            sub_filters={
                "Item Rarity":   "Rare",
                "Item Level":    78,
                "Listed":        "Up to 2 weeks ago",
                "Identified":    "Yes",
                "Item Category": "Body Armour",
                "Searched Item": "Expert Altar Robe",
            },
            output_path="C:/full/path/to/exported_file.xlsx",
            wait_interval=15
        )
    """

    import os
    import time
    import pyautogui
    import pandas as pd
    from datetime import datetime
    import json
    import subprocess
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    # Default sub_filters for testing if none provided
    if sub_filters is None:
        sub_filters = {
            "Item Rarity": "Rare",
            "Listed": "Up to 2 weeks ago",
            "Identified": "Yes",
        }

    FILTER_TOGGLES = {
        "Type Filters":      "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[2]/div/div[1]/div[1]/div[1]/div/span[1]/button",
        "Equipment Filters": "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[2]/div/div[1]/div[2]/div[1]/div/span[1]/button",
        "Requirements":      "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[2]/div/div[1]/div[3]/div[1]/div/span[1]/button",
        "Waystone Filters":  "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[2]/div/div[1]/div[4]/div[1]/div/span[1]/button",
        "Miscellaneous":     "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[2]/div/div[1]/div[5]/div[1]/div/span[1]/button",
        "Trade Filters":     "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[2]/div/div[1]/div[6]/div[1]/div/span[1]/button",
        "Stat Filters":      "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[2]/div/div[1]/div[7]/div[1]/div/span[1]/button"
    }

    BUYOUT_INTERVALS = []
    # 10‑point intervals from 10 to 449
    for start in range(10, 450, 10):
        BUYOUT_INTERVALS.append((start, start + 9))
    # Then thirty 450‑point intervals, final one open‑ended
    for i in range(30):
        start = 450 * (i + 1)
        end = start + 449
        if i == 29:
            BUYOUT_INTERVALS.append((start, None))
        else:
            BUYOUT_INTERVALS.append((start, end))

    apply_sub_filters = True

    # -------------------------------------------------------------------------
    # (Commented out) XPaths approach to selecting the league:
    # -------------------------------------------------------------------------
    """
    def set_league(driver, league_name="PoE2 - Dawn of the Hunt"):
        \"\"\"
        Attempt to select the league from the dropdown using the provided XPaths.
        \"\"\"
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        print(f"=== [INFO] Setting league to '{league_name}' ===")
        try:
            # 1) Click the dropdown button
            dropdown_btn_xpath = "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[1]/div[2]/div[1]/div[3]/span/span"
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, dropdown_btn_xpath))
            ).click()
            time.sleep(1)

            # 2) Click the actual league item (li[2])
            league_item_xpath = "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[1]/div[2]/div[1]/div[3]/ul/li[2]/span/span"
            league_item = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, league_item_xpath))
            )
            league_text = league_item.text.strip()
            league_item.click()

            print(f">>> [INFO] League successfully set to: '{league_text}'")
        except Exception as e:
            print(f">>> [ERROR] Could not set league: {e}")
    """

    # -------------------------------------------------------------------------
    # Internal helper functions
    # -------------------------------------------------------------------------
    def click_show_filters(driver):
        print("=== [INFO] Checking if search-advanced is hidden or not ===")
        try:
            advanced_pane = driver.find_element(By.CSS_SELECTOR, "div.search-bar.search-advanced")
            pane_classes = advanced_pane.get_attribute("class")
            if "search-advanced-hidden" in pane_classes:
                print(">>> [INFO] Filters appear collapsed => attempting to expand.")
                try:
                    show_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Show Filters')]")
                    driver.execute_script("""
                        arguments[0].style.display = 'block';
                        arguments[0].scrollIntoView(true);
                        arguments[0].click();
                    """, show_btn)
                    time.sleep(1)
                    print(">>> [INFO] 'Show Filters' forcibly displayed & clicked via JS.")
                except:
                    print(">>> [INFO] 'Show Filters' text not found. Fallback to XPATH toggle.")
                    try:
                        toggle_xpath = "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[3]/div[3]/button[2]"
                        toggle_btn = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, toggle_xpath))
                        )
                        driver.execute_script("""
                            arguments[0].style.display = 'block';
                            arguments[0].scrollIntoView(true);
                            arguments[0].click();
                        """, toggle_btn)
                        time.sleep(1)
                        print(">>> [INFO] 'Show/Hide Filters' forced via XPATH toggle.")
                    except:
                        print(">>> [INFO] Could not toggle filters via fallback XPATH.")
            else:
                print(">>> [INFO] Filters appear to be expanded, doing nothing.")
        except Exception as e:
            print(f">>> [INFO] Could not find search-advanced pane: {e}")
            print(">>> [INFO] Attempting fallback XPATH toggle anyway.")
            try:
                toggle_xpath = "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[3]/div[3]/button[2]"
                toggle_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, toggle_xpath))
                )
                driver.execute_script("""
                    arguments[0].style.display = 'block';
                    arguments[0].scrollIntoView(true);
                    arguments[0].click();
                """, toggle_btn)
                time.sleep(1)
                print(">>> [INFO] 'Show/Hide Filters' forced via fallback.")
            except Exception as ex:
                print(f">>> [INFO] Fallback toggle button also failed: {ex}")

    def toggle_if_off(driver, xpath_str, group_name):
        try:
            toggle_btn = driver.find_element(By.XPATH, xpath_str)
            btn_class = toggle_btn.get_attribute("class")
            if "off" in btn_class:
                toggle_btn.click()
                time.sleep(1)
                new_class = toggle_btn.get_attribute("class")
                if "off" not in new_class:
                    print(f">>> [INFO] Toggled '{group_name}' ON.")
                else:
                    print(f">>> [INFO] '{group_name}' still 'off' after click.")
            else:
                print(f">>> [INFO] '{group_name}' already ON.")
        except Exception as ex:
            print(f">>> [INFO] Could not toggle '{group_name}': {ex}")

    def apply_sub_filter(driver, fname, fval):
        try:
            filt_title = driver.find_element(
                By.XPATH,
                f"//div[contains(@class,'filter-title') and contains(normalize-space(), '{fname}')]"
            )
            filt_parent = filt_title.find_element(
                By.XPATH,
                "./ancestor::span[contains(@class,'filter-body')] | ./ancestor::div[contains(@class,'filter-property')]"
            )
            if fname == "Seller Account":
                txt_in = filt_parent.find_element(By.CSS_SELECTOR, "input.form-control.text")
                txt_in.clear()
                txt_in.send_keys(fval)
                time.sleep(1)
                print(f">>> [INFO] Sub-filter '{fname}' set to '{fval}'.")
            else:
                dd_in = filt_parent.find_element(
                    By.CSS_SELECTOR,
                    "div.multiselect.filter-select input.multiselect__input"
                )
                dd_in.click()
                time.sleep(1)
                dd_in.clear()
                dd_in.send_keys(fval)
                time.sleep(1)
                dd_in.send_keys(Keys.RETURN)
                time.sleep(1)
                print(f">>> [INFO] Sub-filter '{fname}' set to '{fval}'.")
        except Exception as ex:
            print(f">>> [INFO] Could not apply filter '{fname}': {ex}")

    def find_buyout_price_inputs(driver):
        print("=== [INFO] Locating 'Buyout Price' inputs ===")
        try:
            buyout_title = driver.find_element(
                By.XPATH,
                "//div[contains(@class,'filter-title') and contains(normalize-space(), 'Buyout Price')]"
            )
            buyout_parent = buyout_title.find_element(
                By.XPATH,
                "./ancestor::span[contains(@class,'filter-body')] | ./ancestor::div[contains(@class,'filter-property')]"
            )
            inputs = buyout_parent.find_elements(By.CSS_SELECTOR, "input.form-control.minmax")
            if len(inputs) < 2:
                print(">>> [INFO] Did not find 2 numeric inputs for 'Buyout Price'.")
                return (None, None)
            print(">>> [INFO] Found 'Buyout Price' min & max input fields.")
            return (inputs[0], inputs[1])
        except Exception as e:
            print(f">>> [INFO] Could not locate 'Buyout Price' filter inputs: {e}")
            return (None, None)

    def set_buyout_price_range(driver, min_input, max_input, min_val, max_val):
        print(f"=== [INFO] Setting Buyout Price: min={min_val}, max={max_val} ===")
        try:
            min_input.clear()
            if min_val is not None:
                min_input.send_keys(str(min_val))
            max_input.clear()
            if max_val is not None:
                max_input.send_keys(str(max_val))
            time.sleep(1)
        except Exception as e:
            print(f">>> [INFO] Could not set buyout price range: {e}")

    def set_item_description(driver, description=""):
        print(f"=== [INFO] Setting Item Description to '{description}' ===")
        try:
            desc_input = driver.find_element(
                By.XPATH,
                "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[1]/div[1]/div/div[2]/input"
            )
            desc_input.clear()
            desc_input.send_keys(description)
            desc_input.send_keys(Keys.ENTER)
            time.sleep(1)
        except Exception as e:
            print(f">>> [INFO] Could not set Item Description: {e}")

    def set_item_level(driver, sub_filters):
        """
        Reads 'Item Level' from sub_filters (default=1 if not provided),
        then sets that value in the search panel.
        """
        level = sub_filters.get("Item Level", 1)
        print(f"=== [INFO] Setting Item Level to '{level}' ===")
        try:
            level_input = driver.find_element(
                By.XPATH,
                "/html/body/div[1]/div/div[1]/div[5]/div[4]/div/div[2]/div/div[1]/div[1]/div[2]/div[3]/span/input[1]"
            )
            level_input.clear()
            level_input.send_keys(str(level))
            time.sleep(1)
        except Exception as e:
            print(f">>> [INFO] Could not set Item Level: {e}")

    def parse_current_items(driver, global_seen_ids):
        items = []
        item_elems = driver.find_elements(By.CSS_SELECTOR, "div.row[data-id]")
        for elem in item_elems:
            data_id = elem.get_attribute("data-id")
            if data_id not in global_seen_ids:
                global_seen_ids.add(data_id)
                try:
                    item_name = elem.find_element(By.CLASS_NAME, "itemPopupContainer").text.strip()
                except:
                    item_name = "Unknown"
                try:
                    stats_sec = elem.find_element(By.CLASS_NAME, "itemPopupAdditional")
                    stats = stats_sec.text.strip().split("\n")
                    stats_str = "\n".join(stats)
                except:
                    stats_str = ""
                try:
                    price = elem.find_element(By.CLASS_NAME, "price").text.strip()
                except:
                    price = "Unknown"
                try:
                    seller = elem.find_element(By.CLASS_NAME, "seller-name").text.strip()
                except:
                    seller = "Unknown"
                try:
                    right_div = elem.find_element(By.CLASS_NAME, "right")
                    right_text = right_div.text.strip()
                except:
                    right_text = ""
                try:
                    left_div = elem.find_element(By.CLASS_NAME, "left")
                    img_element = left_div.find_element(By.TAG_NAME, "img")
                    img_url = img_element.get_attribute("src")
                except:
                    img_url = ""
                item_dict = {
                    "ID": data_id,
                    "Name": item_name,
                    "Stats": stats_str,
                    "Price": price,
                    "Seller": seller,
                    "Left": img_url,
                    "Right": right_text
                }
                print(f"[NEW ITEM ADDED] ID: {data_id} | Name: {item_name}")
                items.append(item_dict)
        return items

    def infinite_scroll_with_item_parse(driver, global_seen_ids):
        final_items = []
        consecutive_no_change = 0
        old_count = 0
        old_height = 0

        while True:
            new_data = parse_current_items(driver, global_seen_ids)
            if new_data:
                final_items.extend(new_data)

            new_count = len(final_items)
            current_height = driver.execute_script("return document.body.scrollHeight")

            if (new_count == old_count) and (current_height == old_height):
                consecutive_no_change += 1
            else:
                consecutive_no_change = 0

            if consecutive_no_change >= 3:
                print(">>> [INFO] Reached end: no more new items & no scroll height change.")
                break

            old_count = new_count
            old_height = current_height
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        return final_items

    # -------------------------------------------------------------------------
    # Main scraping steps
    # -------------------------------------------------------------------------
    # Launch Chrome in debug mode
    pyautogui.hotkey("win", "r")
    time.sleep(1)
    pyautogui.typewrite('chrome --remote-debugging-port=9222 --user-data-dir="C:\\selenium\\ChromeProfile"\n')
    time.sleep(1)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(1)
    pyautogui.write("https://www.pathofexile.com/trade2/", interval=0.05)
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(10)

    print("\n=== [INFO] Attaching Selenium to Chrome ===")
    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=options)

    try:
        # ---------------------------------------------------------------------
        # 'Hack' approach to select league:
        # ---------------------------------------------------------------------
        print("=== [INFO] Using hack approach: Press Tab, type the league, Enter ===")
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.typewrite("PoE2 - Dawn of the Hunt", interval=0.05)
        pyautogui.press("enter")
        time.sleep(1)

        click_show_filters(driver)
        print("=== [INFO] Toggling all filter groups ON if 'off' ===")
        for gname, gxpath in FILTER_TOGGLES.items():
            toggle_if_off(driver, gxpath, gname)

        print("\n=== [INFO] Applying sub-filters now ===")
        if apply_sub_filters and sub_filters:
            for n, v in sub_filters.items():
                if n == "Item Category" or n == 'Search Item':
                    v = v.replace("_", " ").title()
                apply_sub_filter(driver, n, v)

        print("\n=== [INFO] Setting Item Description and Item Level ===")
        searched_item = sub_filters.get("Searched Item", "")
        set_item_description(driver, searched_item)
        set_item_level(driver, sub_filters)

        print("\n=== [INFO] Locating 'Buyout Price' fields ===")
        buyout_min_input, buyout_max_input = find_buyout_price_inputs(driver)
        if not buyout_min_input or buyout_max_input is None:
            print(">>> [INFO] Could not find 'Buyout Price' fields. Exiting.")
            return

        print("\n=== [INFO] Preparing for multiple Buyout Price searches ===")
        all_items = []
        global_seen_ids = set()

        # Track how many consecutive intervals have returned zero new items.
        consecutive_zero_results = 0

        for (min_val, max_val) in BUYOUT_INTERVALS:
            # Track start time so we can enforce a minimum wait_interval
            interval_start = time.time()

            pyautogui.moveRel(0, 100, duration=0.5)
            pyautogui.moveRel(0, -100, duration=0.5)
            set_buyout_price_range(driver, buyout_min_input, buyout_max_input, min_val, max_val)
            print(f"\n=== [INFO] Searching with min={min_val}, max={max_val} ===")
            try:
                search_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.search-btn"))
                )
                search_btn.click()
                print(">>> [INFO] Search clicked.")
            except Exception as e:
                print(f">>> [INFO] Could not click 'Search': {e}")
                # Enforce wait_interval even if search fails quickly
                elapsed = time.time() - interval_start
                if elapsed < wait_interval:
                    time.sleep(wait_interval - elapsed)
                continue

            time.sleep(5)
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "results"))
                )
            except:
                print(">>> [INFO] No .results container found for this range, skipping.")
                # Mark as zero results, then see if we've hit 3 in a row
                consecutive_zero_results += 1
                if consecutive_zero_results >= 3:
                    print(">>> [INFO] 3 consecutive intervals had no items. Skipping remaining intervals.")
                    break
                # Enforce wait_interval
                elapsed = time.time() - interval_start
                if elapsed < wait_interval:
                    time.sleep(wait_interval - elapsed)
                continue

            # Parse items for this range
            items_for_this_range = infinite_scroll_with_item_parse(driver, global_seen_ids)
            count_new = len(items_for_this_range)
            print(f">>> [INFO] Found {count_new} new items (min={min_val}, max={max_val})")
            all_items.extend(items_for_this_range)

            # Update consecutive zero results
            if count_new == 0:
                consecutive_zero_results += 1
            else:
                consecutive_zero_results = 0

            # If we have 3 intervals in a row with no new items, skip further intervals
            if consecutive_zero_results >= 3:
                print(">>> [INFO] 3 consecutive intervals had no items. Skipping remaining intervals.")
                break

            # Make sure each interval takes at least wait_interval seconds total
            elapsed = time.time() - interval_start
            if elapsed < wait_interval:
                time.sleep(wait_interval - elapsed)

            # If we aren't at last interval, prepare for the next
            if (min_val, max_val) != BUYOUT_INTERVALS[-1]:
                print("=== [INFO] Finished scraping, scrolling back to top... ===")
                driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
                time.sleep(2)
                print("=== [INFO] Re-clicking 'Show Filters' to set next range... ===")
                click_show_filters(driver)
                pyautogui.moveRel(0, 1, duration=0.1)
                pyautogui.moveRel(0, -1, duration=0.1)
                time.sleep(5)
            else:
                print("=== [INFO] Finished scraping all intervals. ===")

        # ---------------------------------------------------------------------
        # Build DataFrame and Save
        # ---------------------------------------------------------------------
        df = pd.DataFrame(all_items)
        total_items = len(df)
        print(f"\n=== [INFO] Number of final scraped items: {total_items} ===")

        if output_path:
            outdir = os.path.dirname(output_path)
            if outdir and not os.path.exists(outdir):
                os.makedirs(outdir)
            df.to_excel(output_path, index=False)
            print(f"\n=== [INFO] Final item list exported to {output_path} - total items: {total_items} ===")
        else:
            print("=== [INFO] No output_path was provided, so file was not saved. ===")

    finally:
        print("\n=== [INFO] Done - Closing browser ===")
        try:
            driver.quit()
        except:
            pass
        print("=== [INFO] Killing Chrome debug session ===")
        subprocess.run("taskkill /F /IM chrome.exe /T", shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
