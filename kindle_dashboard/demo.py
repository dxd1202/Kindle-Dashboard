"""Fixed display data for an offline preview."""

from datetime import datetime, timedelta
import json

from .config import ASSETS, BEIJING

DEMO_NOW = datetime(2026, 11, 16, 11, 30, tzinfo=BEIJING)
DEMO_SETTINGS = {
    "semester": {"start": "2026-09-14", "weeks": 18},
    "tasks": [
        {"title": "数电预习", "due": "2026-11-16T23:59"},
        {"title": "物理报告", "due": "2026-11-19T18:00"},
        {"title": "整理实验板和导线"},
        {"title": "复习法语疑问句"},
    ],
}


def demo_data(now):
    icon_map = json.loads((ASSETS / "qweather-icons.json").read_text(encoding="utf-8"))
    demo_weather = [
        ("100", "晴", 3, 14), ("101", "多云", 4, 13), ("305", "小雨", 5, 10),
        ("104", "阴", 3, 11), ("100", "晴", 2, 13), ("100", "晴", 3, 14),
        ("101", "多云", 4, 15),
    ]
    forecast = {
        (now.date() + timedelta(days=i)).isoformat(): {
            "icon": chr(int(icon_map[code])), "condition": condition, "low": low, "high": high,
            "humidity": (0.52, 0.61, 0.78, 0.64, 0.41, 0.43, 0.55)[i],
        } for i, (code, condition, low, high) in enumerate(demo_weather)
    }
    air_quality = {
        (now.date() + timedelta(days=i)).isoformat(): str(value)
        for i, value in enumerate((68, 53, 42))
    }
    schedule = {
        now.date(): [
            {"time": "09:50", "name": "大学物理", "place": "六教"},
            {"time": "14:30", "name": "数电实验", "place": "实验室"},
            {"time": "19:00", "name": "排球训练", "place": "综合体育馆"},
        ],
        now.date() + timedelta(days=1): [
            {"time": "08:00", "name": "数据结构", "place": "三教"},
            {"time": "15:20", "name": "法语课", "place": "文南楼"},
        ],
    }
    return forecast, air_quality, schedule
