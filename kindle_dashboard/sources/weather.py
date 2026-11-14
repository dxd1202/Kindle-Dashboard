from datetime import datetime
import json
import os
from urllib.parse import urlsplit

import requests

from ..config import ASSETS, BEIJING, WEATHER_LOCATION

ICON_DATA_FILE = ASSETS / "qweather-icons.json"


def load_icon_map():
    if not ICON_DATA_FILE.is_file():
        print("[天气] 找不到天气图标码表")
        return {}
    with ICON_DATA_FILE.open(encoding="utf-8") as stream:
        return json.load(stream)


ICON_MAP = load_icon_map()


def get_icon_char(icon_id):
    return chr(int(ICON_MAP.get(str(icon_id), ICON_MAP.get("999", 61766))))


def request_qweather(endpoint, *, service="weather", **params):
    host = os.environ["WEATHER_HOST"].strip()
    url = urlsplit(host if "://" in host else f"https://{host}")
    if url.scheme != "https" or not url.hostname or url.username is not None:
        raise ValueError("WEATHER_HOST 应为和风天气的 HTTPS API Host")
    if service in ("weather", "weatheralert"):
        params["localTime"] = "true"
    coordinates = f"{WEATHER_LOCATION.latitude}/{WEATHER_LOCATION.longitude}"
    response = requests.get(
        f"https://{url.netloc}/{service}/v1/{endpoint}/{coordinates}",
        params={"lang": "zh", **params},
        headers={"X-QW-Api-Key": os.environ["WEATHER_KEY"].strip()},
        allow_redirects=False,
        timeout=10,
    )
    if response.status_code != 200:
        print(f"[天气] 和风天气 {service}/{endpoint} 返回 HTTP {response.status_code}")
        raise ValueError("和风天气请求失败")
    return response.json()


def local_time(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return stamp.replace(tzinfo=BEIJING) if stamp.tzinfo is None else stamp.astimezone(BEIJING)


def get_daily_forecast():
    try:
        forecast = {}
        for entry in request_qweather("daily", days=7)["days"]:
            day = local_time(entry["forecastStartTime"]).date().isoformat()
            daytime = entry["daytime"]
            condition = daytime["condition"]
            forecast[day] = {
                "icon": get_icon_char(condition["code"]),
                "condition": condition["text"],
                "low": round(entry["temperatureMin"]["value"]),
                "high": round(entry["temperatureMax"]["value"]),
                "humidity": daytime.get("humidity"),
            }
        return forecast
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
        print(f"[天气] 七天预报获取失败: {type(error).__name__}")
        return {}


def get_daily_aqi():
    try:
        result = {}
        for entry in request_qweather("daily", service="airquality")["days"]:
            day = local_time(entry["forecastStartTime"]).date().isoformat()
            for index in entry.get("indexes", ()):
                if index.get("code") == "cn-mee":
                    display = index.get("aqiDisplay")
                    if display is not None and str(display).strip():
                        result[day] = str(display).strip()
                    break
        return result
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
        print(f"[天气] 每日 AQI 获取失败: {type(error).__name__}")
        return {}


def get_weather_alerts(now):
    """Return active alert labels, or None when alert status could not be checked."""
    try:
        data = request_qweather("current", service="weatheralert")
        if data.get("metadata", {}).get("zeroResult") is True:
            return []

        alerts = data["alerts"]
        superseded = {
            alert_id for alert in alerts
            for alert_id in ((alert.get("messageType") or {}).get("supersedes") or ())
        }
        active = []
        for alert in alerts:
            if alert.get("id") in superseded or (alert.get("messageType") or {}).get("code") == "cancel":
                continue
            expires = alert.get("expireTime")
            if expires and local_time(expires) <= now:
                continue
            active.append(alert)
        severity = {"extreme": 0, "severe": 1, "moderate": 2, "minor": 3}
        active.sort(key=lambda alert: severity.get(alert.get("severity"), 4))
        labels = {}
        colors = {"red": "红色", "orange": "橙色", "yellow": "黄色", "blue": "蓝色"}
        for alert in active:
            event_type = alert.get("eventType") or {}
            event = event_type.get("name")
            color_code = (alert.get("color") or {}).get("code")
            color = colors.get(color_code)
            headline = alert.get("headline")
            label = f"{event}{color}预警" if event and color else headline or event or "天气预警"
            event_key = event_type.get("code") or event
            level = color_code or alert.get("severity")
            if event_key and level:
                key = ("event", event_key, level)
            else:
                key = ("record", alert.get("id") or headline or len(labels))
            labels.setdefault(key, label)
        return list(labels.values())
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
        print(f"[天气] 实时预警获取失败: {type(error).__name__}")
        return None


def get_open_meteo_forecast():
    """Fetch the configured location's forecast without an API key."""
    conditions = {
        0: ("100", "晴"), 1: ("101", "少云"), 2: ("101", "多云"), 3: ("104", "阴"),
        45: ("501", "雾"), 48: ("501", "冻雾"),
        51: ("305", "小毛毛雨"), 53: ("305", "毛毛雨"), 55: ("305", "密集毛毛雨"),
        56: ("313", "小冻毛毛雨"), 57: ("313", "冻毛毛雨"),
        61: ("305", "小雨"), 63: ("306", "中雨"), 65: ("307", "大雨"),
        66: ("313", "小冻雨"), 67: ("313", "冻雨"),
        71: ("400", "小雪"), 73: ("401", "中雪"), 75: ("402", "大雪"), 77: ("400", "雪粒"),
        80: ("300", "小阵雨"), 81: ("300", "阵雨"), 82: ("301", "强阵雨"),
        85: ("407", "小阵雪"), 86: ("407", "强阵雪"),
        95: ("302", "雷阵雨"), 96: ("304", "雷雨伴冰雹"), 99: ("304", "雷雨伴冰雹"),
    }
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": WEATHER_LOCATION.latitude,
                "longitude": WEATHER_LOCATION.longitude,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "timezone": "Asia/Shanghai", "forecast_days": 7,
            },
            timeout=10,
        )
        response.raise_for_status()
        daily = response.json()["daily"]
        forecast = {}
        for day, code, low, high in zip(
            daily["time"], daily["weather_code"],
            daily["temperature_2m_min"], daily["temperature_2m_max"], strict=True,
        ):
            if low is None or high is None:
                continue
            icon, condition = conditions.get(code, ("999", "未知"))
            forecast[day] = {
                "icon": get_icon_char(icon), "condition": condition,
                "low": round(low), "high": round(high),
            }
        return forecast
    except (requests.RequestException, ValueError, TypeError, KeyError, OverflowError) as error:
        print(f"[天气] Open-Meteo 获取失败: {type(error).__name__}")
        return {}
