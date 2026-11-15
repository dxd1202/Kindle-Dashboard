from datetime import timedelta
from math import isfinite

from ..config import WEATHER_LOCATION, WEEKDAYS
from .widgets import BLACK, DARK, FOOTER_RULE_Y, LEFT, MUTED, PALE, RIGHT, WEATHER_WIDTH

DETAIL_SIZE = 35
COLD_TEMPERATURE, HOT_TEMPERATURE = 0, 35
LOW_HUMIDITY, HIGH_HUMIDITY = 30, 85
HIGH_AQI, HIGH_UV = 101, 6


def humidity_percent(value):
    return round(value * 100) if isinstance(value, (int, float)) and 0 <= value <= 1 else None


def emphasis(value, *, low=None, high=None, gray=BLACK):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return {"gray": gray, "bold": False}
    flagged = isfinite(number) and (
        (low is not None and number <= low) or (high is not None and number >= high)
    )
    return {"gray": BLACK if flagged else gray, "bold": flagged}


def current_weather_row(widgets, left, right, top, bottom, weather):
    widgets.rect(left, top, right, bottom, 245)
    text = widgets.text
    current = weather.current or {}
    center = (top + bottom) // 2
    heading_y = center - (29 if current else 19)
    conditions_y = center + 17
    text(left + 12, heading_y, "当前天气", 30, bold=True, center_y=True)
    if current:
        text(left + 138, heading_y, f"{current['observed_at']:%H:%M} 实况", 30,
             gray=MUTED, center_y=True)
        text(left + 41, conditions_y, current["icon"], 52, align="center",
             font="qweather-icons.ttf", center_y=True)
        text(left + 82, conditions_y, f"{current['temperature']}°", 58, bold=True,
             max_width=105, center_y=True, fit_width=True)
        text(left + 196, conditions_y, current["condition"], DETAIL_SIZE, bold=True, center_y=True,
             max_width=113, fit_width=True)
    else:
        text(left + 12, center + 19, "近一小时暂无实况", 32, gray=MUTED, center_y=True)
    widgets.rect(left + 320, top + 12, left + 322, bottom - 12)
    feels = current.get("feels_like")
    humidity = humidity_percent(current.get("humidity"))
    uv = current.get("uv_index")
    aqi = weather.current_aqi
    upper, lower = center - 19, center + 19
    text(left + 335, upper, f"体感 {feels}°" if feels is not None else "体感 —",
         DETAIL_SIZE, center_y=True, max_width=105, fit_width=True,
         **emphasis(feels, low=COLD_TEMPERATURE, high=HOT_TEMPERATURE))
    text(right - 12, upper, f"湿度 {humidity}%" if humidity is not None else "湿度 —",
         DETAIL_SIZE, align="right", center_y=True, max_width=139, fit_width=True,
         **emphasis(humidity, low=LOW_HUMIDITY, high=HIGH_HUMIDITY))
    text(left + 335, lower, f"UV {uv}" if uv is not None else "UV —", DETAIL_SIZE, center_y=True,
         max_width=69, fit_width=True, **emphasis(uv, high=HIGH_UV))
    text(right - 12, lower, f"实时 AQI {aqi or '—'}",
         DETAIL_SIZE, align="right", center_y=True, max_width=178, fit_width=True,
         **emphasis(aqi, high=HIGH_AQI))


def add_weather(widgets, today, weather, hide_personal):
    text, rect, line = widgets.text, widgets.rect, widgets.line
    weather_left = (LEFT + RIGHT - WEATHER_WIDTH) // 2 if hide_personal else LEFT
    weather_right = weather_left + WEATHER_WIDTH
    text(weather_left, 174, "未来七天", 70, bold=True, center_y=True)
    location = f"{WEATHER_LOCATION.city} · {WEATHER_LOCATION.district}"
    if weather.source:
        location += f" / {weather.source}"
    text(weather_right, 140, location, DETAIL_SIZE, gray=MUTED, align="right",
         max_width=320, fit_width=True)
    fetched = f"{weather.fetched_at:%H:%M}" if weather.fetched_at else "—"
    text(weather_right, 181, f"预报获取 {fetched}", DETAIL_SIZE, gray=MUTED, align="right")
    weather_top = 376
    weather_bottom = FOOTER_RULE_Y - 10
    if weather.alerts:
        rect(weather_left, 219, weather_right, 266, DARK)
        text(weather_left + 12, 242, " · ".join(weather.alerts), 40, gray=255, bold=True,
             max_width=576, center_y=True, fit_width=True)
    else:
        status = "暂无天气预警" if weather.alerts == [] else "预警暂不可用"
        text(weather_left, 242, status, 40, gray=MUTED, center_y=True)
    current_weather_row(widgets, weather_left, weather_right, 273, weather_top, weather)
    line(weather_left, weather_top - 2, weather_right, DARK)
    days = [today + timedelta(days=index) for index in range(7)]
    entries = [weather.forecast.get(day.isoformat()) for day in days]
    values = [entry[key] for entry in entries if entry for key in ("low", "high")]
    coldest = min(values, default=0)
    scale = max(1, max(values, default=0) - coldest)
    track_left = weather_left + 433
    track_width = 82
    highs = [entry["high"] for entry in entries if entry]
    if highs and all(0 <= high <= 9 for high in highs):
        # Reclaim one digit's space while keeping the same track for all days.
        track_left += 24

    for index, (day, entry) in enumerate(zip(days, entries, strict=True)):
        y = weather_top + index * (weather_bottom - weather_top) // 7
        bottom = weather_top + (index + 1) * (weather_bottom - weather_top) // 7
        row_height = bottom - y
        center = y + row_height // 2
        upper, lower = center - 19, center + 19
        if index == 0:
            rect(weather_left, y, weather_right, bottom, PALE)
        title = ("今天", "明天")[index] if index < 2 else WEEKDAYS[day.weekday()]
        is_today = index == 0
        detail_gray = BLACK if is_today else MUTED
        # The larger weekday glyphs extend farther above the pair's center.
        date_offset = 4 if is_today else 3
        text(weather_left + 12, upper + date_offset, title, 46,
             gray=detail_gray, bold=is_today, center_y=True)
        text(weather_left + 12, lower + date_offset, day.strftime("%m/%d"), DETAIL_SIZE,
             gray=detail_gray, bold=is_today, center_y=True)
        if entry:
            text(weather_left + 151, upper, entry["icon"], 44,
                 align="center", font="qweather-icons.ttf", center_y=True)
            text(weather_left + 151, lower + 2, entry["condition"], DETAIL_SIZE, gray=detail_gray,
                 align="center", max_width=122, center_y=True, fit_width=True)
            low, high = entry["low"], entry["high"]
            text(track_left - 12, center, f"{low}°", 48, gray=detail_gray, align="right",
                 center_y=True, max_width=72, fit_width=True)
            rect(track_left, center - 4, track_left + track_width, center + 5, 205)
            start = track_left + round((low - coldest) * track_width / scale)
            end = track_left + round((high - coldest) * track_width / scale)
            rect(start - 3, center - 6, end + 3, center + 7, DARK)
            text(weather_right - 12, center, f"{high}°", 48, bold=True, align="right",
                 center_y=True, max_width=70, fit_width=True)
        else:
            text(weather_right - 14, center, "—", DETAIL_SIZE, gray=detail_gray,
                 align="right", center_y=True)
        humidity = humidity_percent(entry.get("humidity")) if entry else None
        text(weather_left + 220, upper, f"湿度 {humidity}%" if humidity is not None else "湿度 —",
             DETAIL_SIZE, max_width=124, center_y=True, fit_width=True,
             **emphasis(humidity, low=LOW_HUMIDITY, high=HIGH_HUMIDITY, gray=detail_gray))
        aqi = weather.air_quality.get(day.isoformat(), "—")
        text(weather_left + 220, lower, f"AQI {aqi}", DETAIL_SIZE, max_width=136,
             center_y=True, fit_width=True, **emphasis(aqi, high=HIGH_AQI, gray=detail_gray))
        line(weather_left, bottom - 1, weather_right)
    if not values:
        text(weather_right - 14, weather_bottom - 29, weather.status, 32,
             gray=MUTED, align="right", center_y=True)
