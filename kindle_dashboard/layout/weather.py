from datetime import timedelta

from ..config import WEATHER_LOCATION, WEEKDAYS
from .widgets import DARK, LEFT, MUTED, PALE, RIGHT


def add_weather(widgets, today, weather, hide_personal):
    text, rect, line = widgets.text, widgets.rect, widgets.line
    weather_left = (LEFT + RIGHT - 600) // 2 if hide_personal else LEFT
    weather_right = weather_left + 600
    text(weather_left, 219, "未来七天", 70, bold=True, center_y=True)
    location = f"{WEATHER_LOCATION.city} · {WEATHER_LOCATION.district}"
    if weather.source:
        location += f" / {weather.source}"
    text(weather_right, 188, location, 31, gray=MUTED, align="right")
    fetched = f"{weather.fetched_at:%H:%M}" if weather.fetched_at else "—"
    text(weather_right, 226, f"预报获取 {fetched}", 30, gray=MUTED, align="right")
    weather_top = 329
    if weather.alerts:
        rect(weather_left, 274, weather_right, 321, DARK)
        text(weather_left + 12, 297, " · ".join(weather.alerts), 34, gray=255, bold=True,
             max_width=576, center_y=True, fit_width=True)
    else:
        status = "暂无天气预警" if weather.alerts == [] else "预警暂不可用"
        text(weather_left, 297, status, 34, gray=MUTED, center_y=True)
    line(weather_left, weather_top - 1, weather_right, DARK)
    days = [today + timedelta(days=index) for index in range(7)]
    entries = [weather.forecast.get(day.isoformat()) for day in days]
    values = [entry[key] for entry in entries if entry for key in ("low", "high")]
    coldest = min(values, default=0)
    scale = max(1, max(values, default=0) - coldest)
    track_left = weather_left + 389
    track_width = 131

    for index, (day, entry) in enumerate(zip(days, entries, strict=True)):
        y = weather_top + index * (966 - weather_top) // 7
        bottom = weather_top + (index + 1) * (966 - weather_top) // 7
        row_height = bottom - y
        center = y + row_height // 2
        upper, lower = center - round(row_height * 0.19), center + round(row_height * 0.19)
        if index == 0:
            rect(weather_left, y, weather_right, bottom, PALE)
        title = ("今天", "明天")[index] if index < 2 else WEEKDAYS[day.weekday()]
        is_today = index == 0
        date_gray = 0 if is_today else MUTED
        text(weather_left + 15, upper, title, 40, gray=date_gray, bold=is_today, center_y=True)
        text(weather_left + 15, lower, day.strftime("%m/%d"), 32,
             gray=date_gray, bold=is_today, center_y=True)
        if entry:
            text(weather_left + 145, upper, entry["icon"], min(38, row_height // 2 - 5),
                 align="center", font="qweather-icons.ttf", center_y=True)
            text(weather_left + 145, lower, entry["condition"], 28, gray=MUTED,
                 align="center", max_width=124, center_y=True)
            text(track_left - 17, center, f'{entry["low"]}°', 42,
                 gray=MUTED, align="right", center_y=True)
            rect(track_left, center - 4, track_left + track_width, center + 5, 205)
            start = track_left + round((entry["low"] - coldest) * track_width / scale)
            end = track_left + round((entry["high"] - coldest) * track_width / scale)
            rect(start - 3, center - 6, end + 3, center + 7, DARK)
            text(weather_right - 14, center, f'{entry["high"]}°', 42,
                 align="right", bold=True, center_y=True)
        else:
            text(weather_right - 14, center, "—", 36, gray=MUTED, align="right", center_y=True)
        humidity = entry.get("humidity") if entry else None
        humidity_text = f"{humidity:.0%}" if isinstance(humidity, (int, float)) and 0 <= humidity <= 1 else "—"
        text(weather_left + 215, upper, f"湿度 {humidity_text}", 28, gray=MUTED,
             max_width=120, center_y=True)
        aqi = weather.air_quality.get(day.isoformat(), "—")
        text(weather_left + 215, lower, f"AQI {aqi}", 28, gray=MUTED, max_width=120, center_y=True)
        line(weather_left, bottom - 1, weather_right)
    if not values:
        text(weather_right, 966, weather.status, 25, gray=MUTED, align="right")
