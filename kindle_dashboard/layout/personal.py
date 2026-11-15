from datetime import timedelta

from ..config import WEEKDAYS
from ..tasks import deadline_label
from .widgets import (
    BLACK, DARK, FOOTER_RULE_Y, HEADER_RULE_HEIGHT, HEADER_RULE_Y, LEFT, MUTED, PALE, RIGHT, WEATHER_WIDTH,
)

HEADING_HEIGHT = 72


def add_panel_heading(widgets, left, right, top, title, subtitle="", emphasis=None):
    center = top + HEADING_HEIGHT // 2
    widgets.text(left, center, title, 48, bold=True, center_y=True)
    if subtitle:
        subtitle_x = left + 108
        widgets.text(subtitle_x, center, subtitle, 34, gray=MUTED,
                     max_width=right - subtitle_x, center_y=True, fit_width=True, emphasis=emphasis)
    widgets.line(left, top + HEADING_HEIGHT, right, DARK)


def add_personal(widgets, now, schedule, schedule_status, deadlines, todos):
    today = now.date()
    text, rect, line = widgets.text, widgets.rect, widgets.line
    body_size = 40
    top = HEADER_RULE_Y + HEADER_RULE_HEIGHT
    bottom = FOOTER_RULE_Y - 10
    left = LEFT + WEATHER_WIDTH + 20
    middle = (left + RIGHT) // 2
    left_end, right_start = middle - 10, middle + 10
    heading_to_rows = HEADING_HEIGHT + 9
    schedule_top = top + heading_to_rows
    schedule_limit, schedule_step = 5, 73
    deadline_limit, deadline_step = 4, 81
    lower_rule_height = 2
    rows_height = schedule_limit * schedule_step + deadline_limit * deadline_step
    spare = bottom - schedule_top - lower_rule_height - heading_to_rows - rows_height
    lower_rule = schedule_top + schedule_limit * schedule_step + spare // 2
    rect(left - 11, top + 14, left - 9, bottom)
    rect(middle - 1, top + 14, middle + 1, lower_rule - 15)
    for offset, (x, end) in enumerate(((left, left_end), (right_start, RIGHT))):
        day = today + timedelta(days=offset)
        title = ("今天", "明天")[offset]
        add_panel_heading(widgets, x, end, top, title, f"{day:%m/%d} · {WEEKDAYS[day.weekday()]}")
        entries = sorted(schedule.get(day, ()), key=lambda item: (item["time"] != "全天", item["time"]))
        if not entries:
            text(x + 10, schedule_top + 8, schedule_status if not schedule else "暂无日程", body_size, gray=MUTED)
        upcoming = next((i for i, entry in enumerate(entries) if entry["time"] >= now.strftime("%H:%M")
                         and entry["time"] != "全天"), None) if offset == 0 else None
        for index, entry in enumerate(entries[:schedule_limit]):
            y = schedule_top + schedule_step * index
            highlight = upcoming == index
            if index:
                line(x + 10, y - 2, end - 5)
            if highlight:
                rect(x, y, end, y + 70, PALE)
                rect(x, y, x + 4, y + 70, DARK)
            text(x + 10, y + 21, entry["time"], 38, bold=True, max_width=92,
                 center_y=True, fit_width=True)
            text(x + 110, y + 21, entry["name"], body_size, bold=highlight,
                 max_width=end - x - 116, center_y=True)
            text(x + 110, y + 52, entry.get("place", ""), 33, gray=MUTED,
                 max_width=end - x - 116, center_y=True)
        if len(entries) > schedule_limit:
            text(x + 10, lower_rule - 12, f"另有 {len(entries) - schedule_limit} 项", 26,
                 gray=MUTED, center_y=True)

    line(left, lower_rule, RIGHT, DARK, lower_rule_height)
    upcoming_deadlines = sum(due >= now for due, _ in deadlines)
    lower_top = lower_rule + lower_rule_height
    body_top = lower_top + heading_to_rows
    prefix, count = "7天内有 ", str(upcoming_deadlines)
    add_panel_heading(widgets, left, left_end, lower_top, "截止", f"{prefix}{count} 个DDL",
                      emphasis=(len(prefix), len(prefix) + len(count)))
    add_panel_heading(widgets, right_start, RIGHT, lower_top, "待办")
    rect(middle - 1, lower_top + 14, middle + 1, bottom)
    if not deadlines:
        text(left + 10, body_top + 4, "未来七天暂无截止", body_size, gray=MUTED)
    for index, (due, title) in enumerate(deadlines[:deadline_limit]):
        y = body_top + index * deadline_step
        urgent = due.date() <= today
        if index:
            line(left + 10, y - 3, left_end - 5)
        if urgent:
            rect(left, y, left_end, y + 76, DARK)
        text(left + 10, y + 18, deadline_label(due, now), 32,
             gray=255 if urgent else MUTED, bold=urgent, center_y=True)
        text(left + 10, y + 53, title, body_size, gray=255 if urgent else BLACK,
             bold=urgent, max_width=left_end - left - 20, center_y=True)
    if len(deadlines) > deadline_limit:
        text(left + 10, bottom - 12, f"另有 {len(deadlines) - deadline_limit} 项", 26,
             gray=MUTED, center_y=True)
    if not todos:
        text(right_start, body_top + 4, "暂无待办", body_size, gray=MUTED)
    for task in todos[:3]:
        before = len(widgets.items)
        text(right_start, body_top + 4, task, body_size, max_width=RIGHT - right_start)
        if len(widgets.items) > before:
            widgets.items[-1]["type"] = "todo"
