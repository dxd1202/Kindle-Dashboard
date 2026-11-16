"""Collect dashboard data before composing a layout."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
    current: dict | None = None
    current_aqi: str | None = None
    alert_credits: tuple[str, ...] = ()


def collect_weather():
    from .sources.weather import (
        get_current_aqi, get_current_weather, get_daily_aqi, get_daily_forecast, get_open_meteo_forecast,
        get_weather_alerts,
    )

    weather = WeatherSnapshot()
    configured = os.getenv("WEATHER_KEY") and os.getenv("WEATHER_HOST")
    if not configured:
        weather.forecast = get_open_meteo_forecast()
        if weather.forecast:
            weather.source = "Open-Meteo"
            weather.fetched_at = datetime.now(BEIJING)
        return weather

    with ThreadPoolExecutor(max_workers=5) as executor:
        forecast = executor.submit(get_daily_forecast)
        air_quality = executor.submit(get_daily_aqi)
        alerts = executor.submit(get_weather_alerts, datetime.now(BEIJING))
        current = executor.submit(get_current_weather)
        current_aqi = executor.submit(get_current_aqi)
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
        weather.alerts, weather.alert_credits = alerts.result()
        weather.current = current.result()
        weather.current_aqi = current_aqi.result()
    return weather


@dataclass
class DashboardSnapshot:
    now: datetime
    semester: dict | None
    weather: WeatherSnapshot
    schedule: dict
    schedule_status: str
    deadlines: list
    todos: list
    demo: bool
    hide_personal: bool

    def layout(self):
        from .layout import compose

        return compose(self.now, self.semester, self.weather, self.schedule, self.schedule_status,
                       self.deadlines, self.todos, hide_personal=self.hide_personal, demo=self.demo)


def collect_dashboard(*, demo, offline, hide_personal, include_end=False):
    now = DEMO_NOW if demo else datetime.now(BEIJING)
    settings = DEMO_SETTINGS if demo else load_settings()
    schedule, schedule_status = {}, "日程未配置"
    if demo:
        forecast, air_quality, schedule = demo_data(now)
        weather = WeatherSnapshot(forecast, air_quality, now, ["大风蓝色预警（示例）"])
        weather.current = {
            "observed_at": now - timedelta(minutes=12),
            "icon": forecast[now.date().isoformat()]["icon"],
            "condition": "晴",
            "temperature": 10,
            "feels_like": 8,
            "humidity": 0.49,
            "uv_index": 2,
        }
        weather.current_aqi = "56"
    elif offline:
        weather = WeatherSnapshot(status="离线模式")
    else:
        weather = collect_weather()

    deadlines, todos = [], []
    if not hide_personal:
        if not demo:
            from .sources.timetable import get_two_day_schedule

            calendar_path = settings.get("calendar")
            path = ROOT / calendar_path if calendar_path else None
            schedule, schedule_status = get_two_day_schedule(now, path, include_end=include_end)
        tasks_path = None if demo else task_file(settings)
        deadlines, todos = dashboard_tasks(settings, now.date(), path=tasks_path)

    return DashboardSnapshot(now, settings.get("semester"), weather, schedule, schedule_status,
                             deadlines, todos, demo, hide_personal)


def build_dashboard(*, demo, offline, hide_personal):
    return collect_dashboard(demo=demo, offline=offline, hide_personal=hide_personal).layout()
