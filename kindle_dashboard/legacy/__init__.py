"""Compatibility entry point for explicit --config layouts."""

import json
from importlib import import_module
import os
from time import perf_counter

from ..config import ROOT
from . import clock


def collect(config, show_timetable):
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    for name, configured in (
        ("weather", os.getenv("WEATHER_KEY") and os.getenv("WEATHER_HOST")),
        ("stock", os.getenv("STOCK_LIST")),
    ):
        started = perf_counter()
        if not configured:
            print(f"[{name}] 未配置", flush=True)
            continue

        try:
            import_module(f".{name}", __package__).update(config)
        except ModuleNotFoundError as error:
            if name != "stock" or error.name != "yfinance":
                raise
            print("[行情] 需要安装可选依赖：python -m pip install -r requirements-legacy.txt",
                  flush=True)
        print(f"[{name}] {perf_counter() - started:.2f} s", flush=True)

    if show_timetable:
        from . import timetable

        started = perf_counter()
        timetable.update(config)
        print(f"[timetable] {perf_counter() - started:.2f} s", flush=True)


def load_layout(path, *, offline, hide_personal):
    with path.open(encoding="utf-8") as stream:
        config = json.load(stream)
    if hide_personal:
        config["widgets"] = [widget for widget in config["widgets"] if widget.get("id") != "timetable"]
    clock.update(config)
    if not offline:
        collect(config, show_timetable=not hide_personal)
    return config
