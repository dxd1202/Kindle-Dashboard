"""Shared paths, Beijing time, and local configuration."""

from dataclasses import dataclass
from datetime import timedelta, timezone
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BUILD = ROOT / "build"
BEIJING = timezone(timedelta(hours=8))
WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


@dataclass(frozen=True)
class WeatherLocation:
    city: str
    district: str
    latitude: float
    longitude: float


WEATHER_LOCATION = WeatherLocation("北京", "海淀", 39.96, 116.31)


def load_settings():
    local = ROOT / "dashboard.local.json"
    settings = json.loads(local.read_text(encoding="utf-8")) if local.is_file() else {}
    if not isinstance(settings, dict):
        raise ValueError("dashboard.local.json 应包含一个 JSON 对象")
    if not settings.get("semester") and os.getenv("SEMESTER_START"):
        settings["semester"] = {
            "start": os.environ["SEMESTER_START"],
            "weeks": int(os.getenv("SEMESTER_WEEKS") or "18"),
        }
    return settings
