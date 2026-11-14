from datetime import timedelta

from ..config import WEEKDAYS
from ..tasks import deadline_label
from .widgets import DARK, MUTED, PALE, RIGHT


def add_personal(widgets, now, schedule, schedule_status, deadlines, todos):
    today = now.date()
    text, rect, line = widgets.text, widgets.rect, widgets.line
    title_size, body_size = 45, 30
    rect(687, 188, 689, 974)
    rect(1049, 188, 1051, 608)
    for offset, (x, end) in enumerate(((718, 1031), (1070, RIGHT))):
        day = today + timedelta(days=offset)
        title = ("今天", "明天")[offset]
        text(x, 188, title, title_size, bold=True)
        text(x + 104, 201, f"{day:%m/%d} · {WEEKDAYS[day.weekday()]}", 28, gray=MUTED)
        line(x, 254, end, DARK)
        entries = sorted(schedule.get(day, ()), key=lambda item: (item["time"] != "全天", item["time"]))
        if not entries:
            text(x + 13, 274, schedule_status if not schedule else "暂无日程", body_size, gray=MUTED)
        upcoming = next((i for i, entry in enumerate(entries) if entry["time"] >= now.strftime("%H:%M")
                         and entry["time"] != "全天"), None) if offset == 0 else None
        for index, entry in enumerate(entries[:5]):
            y = 267 + 62 * index
            highlight = upcoming == index
            if highlight:
                rect(x, y - 5, end, y + 56, PALE)
                rect(x, y - 5, x + 4, y + 56, DARK)
            elif index > 0 and upcoming != index - 1:
                line(x + 13, y - 5, end - 5, 220, 1)
            text(x + 13, y + 14, entry["time"], 30, bold=highlight, center_y=True)
            text(x + 88, y + 14, entry["name"], body_size, bold=highlight,
                 max_width=end - x - 96, center_y=True)
            text(x + 88, y + 41, entry.get("place", ""), 26, gray=MUTED,
                 max_width=end - x - 96, center_y=True)
        if len(entries) > 5:
            text(x + 13, 582, f"另有 {len(entries) - 5} 项", 25, gray=MUTED)

    line(718, 628, RIGHT, DARK)
    text(718, 649, "截止", title_size, bold=True)
    upcoming_deadlines = sum(due >= now for due, _ in deadlines)
    text(821, 674, f"7天内有{upcoming_deadlines}个DDL", 26, gray=MUTED,
         max_width=210, center_y=True)
    text(1070, 649, "待办", title_size, bold=True)
    rect(1049, 652, 1051, 953)
    if not deadlines:
        text(730, 716, "未来七天暂无截止", body_size, gray=MUTED)
    for index, (due, title) in enumerate(deadlines[:4]):
        y = 710 + index * 61
        urgent = due.date() <= today
        if urgent:
            rect(718, y, 1031, y + 57, DARK)
        text(730, y + 14, deadline_label(due, now), 25,
             gray=255 if urgent else MUTED, bold=urgent, center_y=True)
        text(730, y + 39, title, body_size, gray=255 if urgent else DARK,
             bold=urgent, max_width=286, center_y=True)
    if not todos:
        text(1070, 716, "暂无待办", body_size, gray=MUTED)
    for task in todos[:3]:
        before = len(widgets.items)
        text(1070, 715, task, body_size, max_width=RIGHT - 1070)
        if len(widgets.items) > before:
            widgets.items[-1]["type"] = "todo"
