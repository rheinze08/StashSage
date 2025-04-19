import re
import os
from datetime import datetime

def parse_line_for_trade(line: str):
    """
    Parses a single line from the client log to extract trade information
    if it matches the known trade pattern: e.g.
      YYYY/MM/DD HH:MM:SS ... @From <buyer>: Hi, I would like to buy your <item> listed for <amount> <currency>

    Returns a dict with:
      {
        "timestamp": datetime,
        "buyer": str,
        "item_name": str,
        "amount": int,
        "currency": str
      }
    or None if no match is found.
    """
    pattern = (
        r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?'
        r'@From\s(.*?): Hi, I would like to buy your '
        r'(.*?) listed for (\d+)\s(\w+)'
    )
    match = re.search(pattern, line)
    if not match:
        return None

    return {
        "timestamp": datetime.strptime(match.group(1), "%Y/%m/%d %H:%M:%S"),
        "buyer": match.group(2),
        "item_name": match.group(3),
        "amount": int(match.group(4)),
        "currency": match.group(5)
    }

def read_all_log_trades(log_files):
    """
    Reads through the entirety of the given log file paths (list of strings),
    parsing out any valid trade lines, and returns a list of dictionaries.

    Each dict is of the form:
      {
        "timestamp": datetime,
        "buyer": str,
        "item_name": str,
        "amount": int,
        "currency": str
      }

    If you want to filter trades by date, do so after you get the resulting list
    or convert to a DataFrame. For example:
      trades_df = pd.DataFrame(read_all_log_trades(...))
      trades_df = trades_df[trades_df["timestamp"] > some_cutoff]
    """
    all_trades = []
    seen_lines = set()

    for log_file in log_files:
        if not os.path.isfile(log_file):
            continue

        with open(log_file, 'r', encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line in seen_lines:
                    continue
                seen_lines.add(line)

                trade_info = parse_line_for_trade(line)
                if trade_info:
                    all_trades.append(trade_info)

    return all_trades
