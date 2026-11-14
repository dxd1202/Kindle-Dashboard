"""Combine the dashboard panels in drawing order."""

from .header import add_header
from .personal import add_personal
from .weather import add_weather
from .widgets import LEFT, MUTED, RIGHT, Widgets


def compose(now, semester, weather, schedule, schedule_status, deadlines, todos, *,
            hide_personal=False, demo=False):
    widgets = Widgets()
    add_header(widgets, now.date(), semester)
    add_weather(widgets, now.date(), weather, hide_personal)
    if not hide_personal:
        add_personal(widgets, now, schedule, schedule_status, deadlines, todos)
    widgets.line(LEFT, 1000, RIGHT)
    if demo:
        widgets.text(LEFT, 1013, "示例数据", 26, gray=MUTED)
    widgets.text(RIGHT, 1013, f"更新于 {now:%H:%M}", 26, gray=MUTED, align="right")
    return {"widgets": widgets.items}
