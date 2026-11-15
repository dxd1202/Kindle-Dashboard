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
    widgets.text(RIGHT, FOOTER_RULE_Y + 7, f"更新于 {now:%H:%M}", 33, gray=MUTED, align="right")
    return {"widgets": widgets.items}
