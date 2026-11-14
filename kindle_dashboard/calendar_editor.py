"""Add one-time events to the same ICS file the dashboard reads."""

from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from uuid import uuid4

from icalendar import Calendar, Event

from .config import BEIJING, ROOT
from .sources.timetable import calendar_file, courses_between


class CalendarEditor:
    def __init__(self, settings):
        configured = settings.get("calendar")
        self.path = calendar_file(ROOT / configured if configured else None).resolve()
        self.inline = (os.getenv("ICS_DATA") or "").strip()

    def read(self):
        if self.inline:
            data = self.inline.encode("utf-8")
        else:
            try:
                data = self.path.read_bytes()
            except FileNotFoundError:
                calendar = Calendar()
                calendar.add("prodid", "-//Kindle Dashboard//Calendar//EN")
                calendar.add("version", "2.0")
                return "missing", calendar.to_ical()
        return sha256(data).hexdigest(), data

    def snapshot(self):
        revision, data = self.read()
        today = datetime.now(BEIJING).date()
        schedule = courses_between(Calendar.from_ical(data), today, 2)
        return {
            "revision": revision,
            "filename": "ICS_DATA" if self.inline else self.path.name,
            "writable": not self.inline,
            "days": [
                {"date": day.isoformat(), "events": sorted(entries, key=lambda item: (
                    item["time"] != "全天", item["time"]
                ))}
                for day, entries in schedule.items()
            ],
        }

    def update(self, change):
        if self.inline:
            raise ValueError("当前日程来自 ICS_DATA，请改用 ICS 文件后再添加")
        revision, data = self.read()
        if change.get("revision") != revision:
            return False
        if change.get("action") != "add":
            raise ValueError("目前支持新增单次日程")
        title, place = change.get("title"), change.get("place", "")
        if not isinstance(title, str) or not title.strip() or len(title.splitlines()) != 1:
            raise ValueError("请输入单行日程名称")
        if not isinstance(place, str) or len(place.splitlines()) > 1:
            raise ValueError("请输入单行地点")
        start = self.timestamp(change.get("start"))
        end = self.timestamp(change["end"]) if change.get("end") else None
        if end is not None and end <= start:
            raise ValueError("结束时间必须晚于开始时间")
        event = Event()
        event.add("uid", f"{uuid4()}@kindle-dashboard")
        event.add("dtstamp", datetime.now(timezone.utc))
        event.add("dtstart", start)
        if end is not None:
            event.add("dtend", end)
        event.add("summary", title.strip())
        if place.strip():
            event.add("location", place.strip())

        # Keep the source bytes intact, including custom properties and recurrence rules.
        closing = re.search(rb"(?im)^END:VCALENDAR(?=\r?$)", data.rstrip())
        if closing is None or data[closing.end():].strip():
            raise ValueError("找不到 ICS 的日历结束标记")
        newline = b"\r\n" if data[:closing.start()].endswith(b"\r\n") else b"\n"
        updated = data[:closing.start()] + event.to_ical().replace(b"\r\n", newline) + data[closing.start():]
        calendar = Calendar.from_ical(updated)
        courses_between(calendar, start.astimezone(BEIJING).date(), 1)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=self.path.parent) as directory:
            staged = Path(directory) / self.path.name
            staged.write_bytes(updated)
            if self.read()[0] != revision:
                return False
            staged.replace(self.path)
        return True

    @staticmethod
    def timestamp(value):
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", value):
            raise ValueError("请选择日期和时间")
        return datetime.fromisoformat(value).replace(tzinfo=BEIJING).astimezone(timezone.utc)
