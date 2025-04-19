import re
import time
import threading
import socket
from datetime import datetime, timedelta
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = ['Microsoft YaHei', 'DejaVu Sans']
import io
import base64
import discord
import asyncio
import datetime as dt
from requests.utils import quote
from flask import Flask, jsonify, send_file
import aiohttp

from poe2trade.app.config_manager import load_config
from poe2trade.utils.log_utils import read_all_log_trades
from poe2trade.utils.chart_utils import (
    generate_price_chart_for_item,
    generate_offers_table_chart
)

app = Flask(__name__)

TIME_INTERVAL_MINUTES = 10
TIME_INTERVAL_SECONDS = TIME_INTERVAL_MINUTES * 60
TIME_WINDOW_MARGIN = 5
client_day_filter = 30
LOG_FILES = []
trade_history = []
IMG_WIDTH_INCHES = 9
IMG_HEIGHT_INCHES = 5

token = None
API_URL = None
USER_ID = None

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True
client = discord.Client(intents=intents)

last_seen_trades = set()

def init_log_files_from_config(config):
    global LOG_FILES
    LOG_FILES = []
    steam_path = config.get("steam_client_log_dir", "").strip()
    ggg_path = config.get("ggg_client_log_dir", "").strip()
    if steam_path:
        LOG_FILES.append(steam_path)
    if ggg_path:
        LOG_FILES.append(ggg_path)
    print("Configured log files:", LOG_FILES, flush=True)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@app.route('/get-api-url', methods=['GET'])
def get_api_url():
    ip = get_local_ip()
    return jsonify({
        "localhost": "http://127.0.0.1:5000",
        "lan": f"http://{ip}:5000"
    })

def scrape_cycle_trade_data():
    global trade_history
    now = datetime.now()
    cutoff_time = now - timedelta(minutes=TIME_INTERVAL_MINUTES)
    new_trades_this_cycle = []
    print(f"Check for New Trades in Cycle at {now.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    all_trades = read_all_log_trades(LOG_FILES)
    for t in all_trades:
        timestamp = t["timestamp"]
        trade_entry = {
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "buyer": t["buyer"],
            "item_name": t["item_name"],
            "amount": t["amount"],
            "currency": t["currency"]
        }
        trade_history.append(trade_entry)
        if timestamp >= cutoff_time:
            new_trades_this_cycle.append(trade_entry)
    trade_history.sort(key=lambda x: x["timestamp"])
    if new_trades_this_cycle:
        print_new_cycle_trades(new_trades_this_cycle)

def print_new_cycle_trades(trades):
    df = pd.DataFrame(trades)
    if not df.empty:
        df = df[["timestamp", "buyer", "amount", "currency"]]
        print("\n📊 New Trades This Cycle (most recent 3):", flush=True)
        print(df.tail(3).to_string(index=False, header=True), flush=True)

def scrape_logs_loop():
    while True:
        scrape_cycle_trade_data()
        time.sleep(TIME_INTERVAL_SECONDS)

@app.route('/latest-trades', methods=['GET'])
def get_latest_trades():
    now = datetime.now()
    cutoff = now - timedelta(minutes=TIME_INTERVAL_MINUTES + TIME_WINDOW_MARGIN)
    recent_trades = [
        t for t in trade_history
        if datetime.strptime(t["timestamp"], "%Y-%m-%d %H:%M:%S") >= cutoff
    ]
    return jsonify(recent_trades if recent_trades else {"status": "no_new_trades"})

@app.route('/generate-price-chart/<item_name>', methods=['GET'])
def route_generate_price_chart(item_name):
    if not trade_history:
        return jsonify({"status": "no_data_for_item"})
    df = pd.DataFrame(trade_history)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    buffer = generate_price_chart_for_item(item_name, df)
    if buffer is None:
        return jsonify({"status": "no_data_for_item"})
    return send_file(
        buffer,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"{item_name}_price_chart.png"
    )

@app.route('/generate-offers-chart/<item_name>', methods=['GET'])
def route_generate_offers_chart(item_name):
    if not trade_history:
        return jsonify({"status": "no_data_for_item"})
    df = pd.DataFrame(trade_history)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    buffer = generate_offers_table_chart(item_name, df)
    if buffer is None:
        return jsonify({"status": "no_data_for_item"})
    return send_file(
        buffer,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"{item_name}_offers_chart.png"
    )

@client.event
async def on_ready():
    global USER_ID
    print(f"✅ Logged in as {client.user}", flush=True)
    await fetch_api_url()
    USER_ID = int(USER_ID) if USER_ID else None
    if USER_ID is None:
        print("⚠️ USER_ID is not set! Discord bot will not send trade notifications!", flush=True)
    else:
        client.loop.create_task(check_for_new_trades())

async def fetch_api_url():
    global API_URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://127.0.0.1:5000/get-api-url", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    API_URL = data.get("localhost", data.get("lan", "http://127.0.0.1:5000"))
                    print(f"✅ Using API URL: {API_URL}", flush=True)
    except Exception as e:
        print(f"⚠️ Error fetching API URL: {e}", flush=True)
        API_URL = "http://127.0.0.1:5000"

async def check_for_new_trades():
    global last_seen_trades
    await client.wait_until_ready()
    user = await client.fetch_user(USER_ID)
    async with aiohttp.ClientSession() as session:
        while not client.is_closed():
            try:
                async with session.get(f"{API_URL}/latest-trades", timeout=5) as resp:
                    json_response = await resp.json()
                now = datetime.now()
                cutoff = now - timedelta(minutes=TIME_INTERVAL_MINUTES + TIME_WINDOW_MARGIN)
                if isinstance(json_response, dict):
                    if json_response.get("status") == "no_new_trades":
                        print(f"✅ [{now.strftime('%Y-%m-%d %H:%M:%S')}] No new trades detected.", flush=True)
                        await asyncio.sleep(TIME_INTERVAL_SECONDS)
                        continue
                    else:
                        print(f"⚠️ Unexpected response: {json_response}", flush=True)
                        await asyncio.sleep(TIME_INTERVAL_SECONDS)
                        continue
                filtered_trades = [
                    t for t in json_response
                    if datetime.strptime(t["timestamp"], "%Y-%m-%d %H:%M:%S") >= cutoff
                ]
                if not filtered_trades:
                    print(f"✅ [{now.strftime('%Y-%m-%d %H:%M:%S')}] No new trades detected.", flush=True)
                    await asyncio.sleep(TIME_INTERVAL_SECONDS)
                    continue
                print("\n📊 [DEBUG] Trades Retrieved from Server:", flush=True)
                for trade in filtered_trades:
                    print(
                        f" - {trade['timestamp']} | {trade['buyer']} | {trade['item_name']} | "
                        f"{trade['amount']} {trade['currency']}",
                        flush=True
                    )
                for trade in filtered_trades:
                    trade_id = (
                        f"{trade['timestamp']}_{trade['buyer']}_{trade['item_name']}_"
                        f"{trade['amount']}_{trade['currency']}"
                    )
                    if trade_id not in last_seen_trades:
                        print(f"🔄 Transmitting trade to Discord: {trade_id}", flush=True)
                        await user.send(
                            f"📊 **New Trade: {trade['item_name']}**\n"
                            f"{trade['amount']} {trade['currency']} from {trade['buyer']}"
                        )
                        encoded_item = quote(trade["item_name"])
                        price_chart_url = f"{API_URL}/generate-price-chart/{encoded_item}"
                        offers_chart_url = f"{API_URL}/generate-offers-chart/{encoded_item}"
                        async with session.get(price_chart_url, timeout=10) as price_resp:
                            if price_resp.status == 200:
                                price_content = await price_resp.read()
                                price_buffer = io.BytesIO(price_content)
                                price_buffer.seek(0)
                                print(f"📤 Sending price chart for {trade['item_name']}", flush=True)
                                await user.send(file=discord.File(price_buffer, filename=f"{trade['item_name']}_price_chart.png"))
                            else:
                                print(f"⚠️ Failed to retrieve price chart for {trade['item_name']}", flush=True)
                                await user.send(
                                    f"⚠️ No historical price data found for **{trade['item_name']}**."
                                )
                        async with session.get(offers_chart_url, timeout=10) as offers_resp:
                            if offers_resp.status == 200:
                                offers_content = await offers_resp.read()
                                offers_buffer = io.BytesIO(offers_content)
                                offers_buffer.seek(0)
                                print(f"📤 Sending offers chart for {trade['item_name']}", flush=True)
                                await user.send(
                                    file=discord.File(offers_buffer, filename=f"{trade['item_name']}_offers_chart.png")
                                )
                            else:
                                print(f"⚠️ Failed to retrieve offers chart for {trade['item_name']}", flush=True)
                                await user.send(
                                    f"⚠️ No historical offer data found for **{trade['item_name']}**."
                                )
                        last_seen_trades.add(trade_id)
                        print(f"✅ Trade transmitted and marked: {trade_id}", flush=True)
            except Exception as e:
                print(f"⚠️ Error fetching trades: {e}", flush=True)
            await asyncio.sleep(TIME_INTERVAL_SECONDS)

def run_discord_flask_app(config):
    global USER_ID, token
    init_log_files_from_config(config)
    print("DEBUG => Entire config loaded:", config, flush=True)  # <--- Add this to confirm what's really loaded
    print(f"Discord user ID: {config.get('discord_user_id', '').strip()}", flush=True)  # <--- Check the ID
    discord_user_id_str = config.get("discord_user_id", "").strip()
    print("DEBUG => 'discord_user_id' from config:", discord_user_id_str, flush=True)  # <--- Double-check it isn't empty
    USER_ID = int(discord_user_id_str) if discord_user_id_str.isdigit() else None
    token = config.get("discord_bot_token", "").strip()
    if not token:
        print("⚠️ Discord bot token not provided in config!", flush=True)
        return
    if USER_ID is None:
        print("⚠️ No valid Discord ID found. Discord bot not started.", flush=True)
        return
    threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": 5000, "debug": False},
        daemon=True
    ).start()
    threading.Thread(target=scrape_logs_loop, daemon=True).start()
    client.run(token)
