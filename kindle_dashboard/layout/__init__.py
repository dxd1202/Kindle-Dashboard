"""Combine the dashboard panels in drawing order."""

from .header import add_header
from .personal import add_personal
from .weather import add_weather
from .widgets import FOOTER_RULE_Y, LEFT, MUTED, RIGHT, Widgets


def compose(now, semester, weather, schedule, schedule_status, deadlines, todos, *,
            hide_personal=False, demo=False):
    widgets = Widgets()
    add_header(widgets, now.date(), semester)
    add_weather(widgets, now.date(), weather, hide_personal)
    if not hide_personal:
        add_personal(widgets, now, schedule, schedule_status, deadlines, todos)
    widgets.line(LEFT, FOOTER_RULE_Y, RIGHT)
    widgets.text(LEFT, FOOTER_RULE_Y + 7, "Kindle Dashboard designed by dxd", 33, gray=MUTED)
    if demo:
        widgets.text((LEFT + RIGHT) // 2, FOOTER_RULE_Y + 7, "示例数据", 33, gray=MUTED,
                     align="center")
    else:
        providers = []
        if (weather.source == "和风天气" or weather.current or weather.air_quality
                or weather.current_aqi or weather.alerts is not None):
            providers.append("和风天气 https://www.qweather.com")
        if weather.source == "Open-Meteo":
            providers.append("Open-Meteo https://open-meteo.com (CC BY 4.0)")
        if providers:
            widgets.text(850, FOOTER_RULE_Y + (13 if weather.alert_credits else 23),
                         " · ".join(providers), 24, gray=MUTED,
                         align="center", center_y=True, max_width=690, fit_width=True)
        if weather.alert_credits:
            widgets.text(850, FOOTER_RULE_Y + 34, " · ".join(weather.alert_credits),
                         21, gray=MUTED, align="center", center_y=True, max_width=690,
                         fit_width=True)
    widgets.text(RIGHT, FOOTER_RULE_Y + 7, f"更新于 {now:%H:%M}", 33, gray=MUTED, align="right")
    return {"widgets": widgets.items}
