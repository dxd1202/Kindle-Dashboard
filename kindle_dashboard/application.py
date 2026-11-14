"""Collect dashboard data before composing a layout."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
import os

from .config import BEIJING, ROOT, load_settings
from .demo import DEMO_NOW, DEMO_SETTINGS, demo_data
from .tasks import dashboard_tasks, task_file


@dataclass
class WeatherSnapshot:
    forecast: dict = field(default_factory=dict)
    air_quality: dict = field(default_factory=dict)
    fetched_at: datetime | None = None
    alerts: list[str] | None = None
    source: str = ""
    status: str = "预报暂无数据"


def collect_weather():
    from .sources.weather import (
        get_daily_aqi, get_daily_forecast, get_open_meteo_forecast, get_weather_alerts,
    )

    weather = WeatherSnapshot()
    configured = os.getenv("WEATHER_KEY") and os.getenv("WEATHER_HOST")
    if not configured:
        weather.forecast = get_open_meteo_forecast()
        if weather.forecast:
            weather.source = "Open-Meteo"
            weather.fetched_at = datetime.now(BEIJING)
        return weather

    with ThreadPoolExecutor(max_workers=3) as executor:
        forecast = executor.submit(get_daily_forecast)
        air_quality = executor.submit(get_daily_aqi)
        alerts = executor.submit(get_weather_alerts, datetime.now(BEIJING))
        weather.forecast = forecast.result()
        if weather.forecast:
            weather.source = "和风天气"
        else:
            weather.forecast = get_open_meteo_forecast()
            if weather.forecast:
                weather.source = "Open-Meteo"
        if weather.forecast:
            weather.fetched_at = datetime.now(BEIJING)
        weather.air_quality = air_quality.result()
        weather.alerts = alerts.result()
    return weather


def build_dashboard(*, demo, offline, hide_personal):
    from .layout import compose

    now = DEMO_NOW if demo else datetime.now(BEIJING)
    settings = DEMO_SETTINGS if demo else load_settings()
    schedule, schedule_status = {}, "日程未配置"
    if demo:
        forecast, air_quality, schedule = demo_data(now)
        weather = WeatherSnapshot(forecast, air_quality, now, ["大风蓝色预警（示例）"])
    elif offline:
        weather = WeatherSnapshot(status="离线模式")
    else:
        weather = collect_weather()

    deadlines, todos = [], []
    if not hide_personal:
        if not demo:
            from .sources.timetable import get_two_day_schedule

            calendar_path = settings.get("calendar")
            schedule, schedule_status = get_two_day_schedule(
                now, ROOT / calendar_path if calendar_path else None
            )
        tasks_path = None if demo else task_file(settings)
        deadlines, todos = dashboard_tasks(settings, now.date(), path=tasks_path)

    return compose(now, settings.get("semester"), weather, schedule, schedule_status,
                   deadlines, todos, hide_personal=hide_personal, demo=demo)
