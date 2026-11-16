"""Apply a mobile edit to the calendar used by the Pages workflow."""

import json
import os
from pathlib import PurePosixPath

from .calendar_editor import CalendarEditor
from .config import ROOT, load_settings


def mobile_calendar():
    path = PurePosixPath(os.environ.get("ICS_FILE", ""))
    editor = CalendarEditor(load_settings())
    source = ROOT / path
    if (path.is_absolute() or path.suffix.lower() != ".ics"
            or any(part.startswith(".") for part in path.parts)
            or source != source.resolve() or source != editor.path
            or not source.is_file() or editor.inline):
        raise ValueError("手机版日程需要仓库内现有的 ICS 文件")
    return editor


def apply_change(editor, change, *, show_locations):
    if not isinstance(change, dict) or change.get("action") not in ("add", "edit"):
        raise ValueError("未知的日程操作")
    first_day = change.get("first_day")
    if not isinstance(first_day, str):
        raise ValueError("缺少日程日期")
    snapshot = editor.snapshot(first_day)
    if change.get("revision") != snapshot["revision"]:
        raise ValueError("日历已被修改，请刷新后重新编辑")
    if not show_locations:
        place = ""
        if change["action"] == "edit":
            event = next((event for day in snapshot["days"] for event in day["events"]
                          if event["id"] == change.get("id")), None)
            if event is None:
                raise ValueError("找不到该次日程，请刷新后重新编辑")
            place = event.get("place", "")
        change = {**change, "place": place}
    if not editor.update(change):
        raise ValueError("日历已被修改，请刷新后重新编辑")


def main():
    try:
        raw = os.environ["CALENDAR_CHANGE"]
        if len(raw) > 4096:
            raise ValueError("日程修改过长")
        apply_change(mobile_calendar(), json.loads(raw),
                     show_locations=os.environ.get("MOBILE_SHOW_LOCATIONS") == "true")
    except (KeyError, OSError, TypeError, ValueError) as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
