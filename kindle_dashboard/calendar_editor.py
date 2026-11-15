"""Manage individual occurrences in the ICS file the dashboard reads."""

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from uuid import uuid4

from icalendar import Calendar, Event

from .config import BEIJING, ROOT
from .sources.timetable import calendar_file, courses_between, event_datetime

EVENT_BLOCK = re.compile(rb"^BEGIN:VEVENT\r?\n.*?^END:VEVENT(?:\r?\n|$)", re.I | re.M | re.S)


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

    @staticmethod
    def appointments(calendar, today):
        indices = {id(event): index for index, event in enumerate(calendar.walk("VEVENT"))}
        targets = {}

        def details(event, master, original_start, local, recurrence_id):
            # Indices are valid for this file revision only. The occurrence key
            # keeps separate dates of the same repeating event distinguishable.
            key = f"{indices[id(event)]}:{recurrence_id.isoformat() if recurrence_id else ''}"
            targets[key] = (event, master, recurrence_id)
            start = local if isinstance(original_start, datetime) else local.date()
            end = None
            if "DTEND" in event:
                first = event.decoded("DTSTART") if "DTSTART" in event else original_start
                last = event.decoded("DTEND")
                duration = event_datetime(last, BEIJING) - event_datetime(first, BEIJING)
                end = start + duration
            elif "DURATION" in event:
                end = start + event.decoded("DURATION")
            return {"id": key, "start": start.isoformat()[:19],
                    "end": end.isoformat()[:19] if end is not None else "",
                    "all_day": not isinstance(start, datetime), "repeating": recurrence_id is not None}

        schedule = courses_between(calendar, today, 2, event_details=details)
        return schedule, targets

    def snapshot(self, first_day=None):
        revision, data = self.read()
        today = datetime.now(BEIJING).date()
        schedule, _ = self.appointments(Calendar.from_ical(data), self.view_date(first_day, today))
        return {
            "revision": revision,
            "filename": "ICS_DATA" if self.inline else self.path.name,
            "writable": not self.inline,
            "today": today.isoformat(),
            "tomorrow": (today + timedelta(days=1)).isoformat(),
            "days": [
                {"date": day.isoformat(), "events": sorted(entries, key=lambda item: (
                    item["time"] != "全天", item["time"]
                ))}
                for day, entries in schedule.items()
            ],
        }

    def update(self, change):
        if self.inline:
            raise ValueError("当前日程来自 ICS_DATA，请改用 ICS 文件后再修改")
        revision, data = self.read()
        if change.get("revision") != revision:
            return False
        action = change.get("action")
        if action not in ("add", "edit", "delete"):
            raise ValueError("未知的日程操作")
        today = self.view_date(change.get("first_day"), datetime.now(BEIJING).date())
        calendar = Calendar.from_ical(data)
        if action == "add":
            event = Event()
            event.add("uid", f"{uuid4()}@kindle-dashboard")
            day = self.fill_event(event, change)
            updated = self.append_event(data, event)
        else:
            _, targets = self.appointments(calendar, today)
            key = change.get("id")
            if not isinstance(key, str) or key not in targets:
                raise ValueError("找不到该次日程，请重新读取日历")
            event, master, recurrence_id = targets[key]
            blocks = list(EVENT_BLOCK.finditer(data))
            if len(blocks) != len(calendar.walk("VEVENT")):
                raise ValueError("无法安全定位 ICS 中的日程")
            block = blocks[int(key.split(":", 1)[0])]
            append = recurrence_id is not None and "RECURRENCE-ID" not in event
            if action == "delete" and recurrence_id is None:
                updated = data[:block.start()] + data[block.end():]
            else:
                if append:
                    event = deepcopy(master)
                    for name in ("RRULE", "RDATE", "EXRULE", "EXDATE"):
                        event.pop(name, None)
                    original = master.decoded("DTSTART")
                    if isinstance(original, datetime) and original.tzinfo is None:
                        recurrence_id = recurrence_id.replace(tzinfo=None)
                    event.add("recurrence-id", recurrence_id)
                if action == "delete":
                    event.pop("STATUS", None)
                    event.add("status", "CANCELLED")
                    event.pop("DTSTAMP", None)
                    event.add("dtstamp", datetime.now(timezone.utc))
                else:
                    self.fill_event(event, change)
                sequence = int(event.get("SEQUENCE", 0)) + 1
                event.pop("SEQUENCE", None)
                event.add("sequence", sequence)
                if append:
                    updated = self.append_event(data, event)
                else:
                    newline = b"\r\n" if b"\r\n" in block[0] else b"\n"
                    encoded = event.to_ical().replace(b"\r\n", newline)
                    updated = data[:block.start()] + encoded + data[block.end():]
            day = today

        courses_between(Calendar.from_ical(updated), day, 2)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=self.path.parent) as directory:
            staged = Path(directory) / self.path.name
            staged.write_bytes(updated)
            if self.read()[0] != revision:
                return False
            staged.replace(self.path)
        return True

    def fill_event(self, event, change):
        title, place = change.get("title"), change.get("place", "")
        if not isinstance(title, str) or not title.strip() or len(title.splitlines()) != 1:
            raise ValueError("请输入单行日程名称")
        if not isinstance(place, str) or len(place.splitlines()) > 1:
            raise ValueError("请输入单行地点")
        all_day = change.get("all_day", False)
        if type(all_day) is not bool:
            raise ValueError("全天日程标记无效")
        start = self.timestamp(change.get("start"), all_day)
        end = self.timestamp(change["end"], all_day) if change.get("end") else None
        if end is not None and end <= start:
            raise ValueError("结束时间必须晚于开始时间")
        for name in ("DTSTAMP", "DTSTART", "DTEND", "DURATION", "SUMMARY", "LOCATION"):
            event.pop(name, None)
        event.add("dtstamp", datetime.now(timezone.utc))
        event.add("dtstart", start)
        if end is not None:
            event.add("dtend", end)
        event.add("summary", title.strip())
        if place.strip() or "RECURRENCE-ID" in event:
            event.add("location", place.strip())
        return start.astimezone(BEIJING).date() if isinstance(start, datetime) else start

    @staticmethod
    def view_date(value, default):
        return date.fromisoformat(value) if value else default

    @staticmethod
    def append_event(data, event):
        # Keep the source bytes intact, including custom properties and recurrence rules.
        closing = re.search(rb"(?im)^END:VCALENDAR(?=\r?$)", data.rstrip())
        if closing is None or data[closing.end():].strip():
            raise ValueError("找不到 ICS 的日历结束标记")
        newline = b"\r\n" if data[:closing.start()].endswith(b"\r\n") else b"\n"
        return data[:closing.start()] + event.to_ical().replace(b"\r\n", newline) + data[closing.start():]

    @staticmethod
    def timestamp(value, all_day):
        pattern = r"\d{4}-\d{2}-\d{2}" if all_day else r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?"
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            raise ValueError("请选择日期和时间")
        if all_day:
            return date.fromisoformat(value)
        return datetime.fromisoformat(value).replace(tzinfo=BEIJING).astimezone(timezone.utc)
