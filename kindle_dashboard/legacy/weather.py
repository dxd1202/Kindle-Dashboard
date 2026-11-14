"""Weather widgets for the original JSON layout."""

import requests

from ..config import WEATHER_LOCATION
from ..sources.weather import get_icon_char, local_time, request_qweather

WIND_DIRECTIONS = dict(zip(
    ("n", "ne", "e", "se", "s", "sw", "w", "nw"),
    ("北", "东北", "东", "东南", "南", "西南", "西", "西北"),
))


def get_weather_now():
    try:
        data = request_qweather("current")
        observed = local_time(data["validTime"])
        condition = data["condition"]
        temp = round(data["temperature"]["value"])
        feels_like = round(data["feelsLike"]["value"])
        humidity = data["humidity"]
        wind = data["wind"]
        direction = WIND_DIRECTIONS.get(wind["direction"]["compass"], "")
        text = (
            f"({WEATHER_LOCATION.district}{observed:%H:%M})     ▷{condition['text']}    {temp}°C\n"
            f"湿度{humidity:.0%}      {direction}风{wind['scale']}级\n"
            f"体感{feels_like}°C"
        )
        return get_icon_char(condition["code"]), text
    except (requests.RequestException, ValueError, TypeError, KeyError, OverflowError) as error:
        print(f"[天气] 实时获取失败: {type(error).__name__}")
        return "", "实时获取失败"


def get_weather_hourly():
    try:
        hours = request_qweather("hourly", hours=24)["hours"][:24]
        if not hours:
            return "24小时预报暂无数据"
        lines = []
        for start in range(0, len(hours), 6):
            group = hours[start:start + 6]
            times = [f"{local_time(hour['forecastTime']):%H}时" for hour in group]
            icons = [get_icon_char(hour["condition"]["code"]) for hour in group]
            temperatures = [
                f"{hour['condition']['text'][:2]}{round(hour['temperature']['value'])}°"
                for hour in group
            ]
            lines.extend(("▷" + "\t".join(times), "↓" + "\t".join(icons) + "○",
                          "↓" + "\t".join(temperatures) + "○"))
        lines.append("↓────── 和风天气 ──────○")
        return "\n".join(lines)
    except (requests.RequestException, ValueError, TypeError, KeyError, OverflowError) as error:
        print(f"[天气] 24小时预报获取失败: {type(error).__name__}")
        return "24小时预报获取失败"


def update(config):
    icon, current = get_weather_now()
    content = {
        "weather_now": current,
        "weather_icon": icon,
        "weather_hourly": get_weather_hourly(),
    }
    for widget in config.get("widgets", []):
        widget_id = widget.get("id")
        if widget_id in content:
            widget["content"] = content[widget_id]
    return config
