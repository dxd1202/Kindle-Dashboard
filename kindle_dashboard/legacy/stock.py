import json
from math import isfinite
import os

import yfinance as yf


def get_stock_data(symbol, name, currency=None):
    label = f"▷{name}○"
    try:
        history = yf.Ticker(symbol).history(period="7d", auto_adjust=False, timeout=10)
        if history.empty:
            return f"{label} ↓无数据○"

        closes = history["Close"]
        price = float(closes.iloc[-1])
        if not isfinite(price):
            return f"{label} ↓无数据○"

        if currency is None:
            _, _, market = symbol.upper().rpartition(".")
            currency = {"SS": "¥", "SZ": "¥", "HK": "HK$"}.get(market, "")
        detail = f"{currency}{price:.2f}"

        if len(closes) >= 2:
            previous = float(closes.iloc[-2])
            if isfinite(previous) and previous != 0:
                change = (price - previous) / previous * 100
                if isfinite(change):
                    sign = "＋" if change >= 0 else "－"
                    detail += f" ▷{sign}{abs(change):.1f}%"
        return f"{label} ↓{detail}○"
    except Exception as error:
        print(f"[行情] {symbol} 获取失败: {type(error).__name__}")
        return f"{label} ↓获取失败○"


def update(config):
    try:
        watchlist = json.loads(os.environ["STOCK_LIST"])
        if not isinstance(watchlist, list) or not all(
            isinstance(item, list)
            and len(item) in (2, 3)
            and all(isinstance(value, str) for value in item)
            and item[0].strip()
            for item in watchlist
        ):
            raise ValueError("每个标的应为 [代码, 名称] 或 [代码, 名称, 币种]")
        entries = [get_stock_data(*item) for item in watchlist]
        content = "\n".join("\t".join(entries[i:i + 2]) for i in range(0, len(entries), 2))
    except ValueError as error:
        print(f"[行情] 列表格式错误: {error}")
        content = "行情配置错误"

    for widget in config["widgets"]:
        if widget.get("id") == "stock":
            widget["content"] = content
            break
    return config
