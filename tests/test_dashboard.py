import os
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from requests import Timeout

from kindle_dashboard.application import WeatherSnapshot, build_dashboard, collect_weather
from kindle_dashboard.calendar_editor import CalendarEditor
from kindle_dashboard.config import BEIJING
from kindle_dashboard.demo import DEMO_NOW, DEMO_SETTINGS, demo_data
from kindle_dashboard.layout import compose
from kindle_dashboard.layout.header import add_header
from kindle_dashboard.layout.widgets import DARK, Widgets
from kindle_dashboard.sources.timetable import get_two_day_schedule
from kindle_dashboard.task_editor import TaskList
from kindle_dashboard.tasks import dashboard_tasks, task_file


class DashboardTests(unittest.TestCase):
    @patch.dict(os.environ, {"ICS_DATA": "", "ICS_FILE": ""})
    def test_calendar_editor_appends_without_rewriting_existing_events(self):
        source = (
            b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//EN\r\n"
            b"BEGIN:VEVENT\r\nUID:course@test\r\nDTSTAMP:20261116T010000Z\r\n"
            b"DTSTART:20261116T010000Z\r\nRRULE:FREQ=WEEKLY;COUNT=2\r\n"
            b"SUMMARY:Existing class\r\nEND:VEVENT\r\n"
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "calendar.ics"
            path.write_bytes(source + b"END:VCALENDAR\r\n")
            editor = CalendarEditor({"calendar": str(path)})
            revision, _ = editor.read()
            change = {"action": "add", "revision": revision, "title": "排球训练",
                      "place": "体育馆", "start": "2026-11-16T19:00"}
            with self.assertRaisesRegex(ValueError, "结束时间"):
                editor.update({**change, "end": "2026-11-16T18:00"})
            self.assertTrue(editor.update({**change, "end": "2026-11-16T20:00"}))
            self.assertFalse(editor.update(change))
            self.assertTrue(path.read_bytes().startswith(source))
            when = DEMO_NOW.replace(tzinfo=BEIJING)
            schedule, _ = get_two_day_schedule(when, path)
            self.assertEqual(schedule[when.date()], [
                {"name": "Existing class", "time": "09:00", "place": ""},
                {"name": "排球训练", "time": "19:00", "place": "体育馆"},
            ])

    def test_semester_progress_matches_displayed_week(self):
        semester = {"start": "2026-09-14", "weeks": 18}
        for day, label, fill_width in (
            (date(2026, 9, 13), "尚未开学", 0),
            (date(2026, 11, 15), "第 9 / 18 周", 160),
            (date(2026, 11, 16), "第 10 / 18 周", 178),
            (date(2027, 1, 18), "学期已结束", 320),
        ):
            with self.subTest(day=day):
                widgets = Widgets()
                add_header(widgets, day, semester)
                self.assertIn("▷" + label, [item.get("content") for item in widgets.items])
                fill = next(item for item in widgets.items
                            if item.get("top") == 110 and item["gray"] == DARK)
                self.assertEqual(fill["right"] - fill["left"], fill_width)

    def test_alert_states_and_personal_panels(self):
        forecast, aqi, schedule = demo_data(DEMO_NOW)
        settings = {
            **DEMO_SETTINGS,
            "tasks": [
                {"title": f"截止事项 {i}", "due": f"2026-11-{16 + i}T23:59"}
                for i in range(1, 6)
            ] + [{"title": "复习法语疑问句并整理本周课堂笔记和需要复习的重点"}],
        }
        deadlines, todos = dashboard_tasks(settings, DEMO_NOW.date())
        for alerts, label in (
            (["大风蓝色预警", "大雾黄色预警"], "▷大风蓝色预警 · 大雾黄色预警"),
            ([], "暂无天气预警"),
            (None, "预警暂不可用"),
        ):
            with self.subTest(alerts=alerts):
                weather = WeatherSnapshot(forecast, aqi, DEMO_NOW, alerts)
                widgets = compose(DEMO_NOW, settings["semester"], weather, schedule, "",
                                  deadlines, todos)["widgets"]
                text = {widget.get("content") for widget in widgets}
                self.assertIn(label, text)
                self.assertIn("7天内有5个DDL", text)
                self.assertIn("截止事项 4", text)
                self.assertNotIn("截止事项 5", text)
                self.assertEqual([widget["content"] for widget in widgets
                                  if widget.get("type") == "todo"], todos)

    @patch("kindle_dashboard.application.task_file")
    @patch("kindle_dashboard.application.collect_weather", return_value=WeatherSnapshot())
    @patch("kindle_dashboard.application.load_settings")
    @patch("kindle_dashboard.sources.timetable.get_two_day_schedule")
    def test_public_mode_skips_personal_data(self, calendar, settings, _weather, task_path):
        settings.return_value = {"tasks": [{"title": "私人事项", "due": "无效日期"}]}
        widgets = build_dashboard(demo=False, offline=False, hide_personal=True)["widgets"]
        calendar.assert_not_called()
        task_path.assert_not_called()
        text = {widget.get("content") for widget in widgets}
        self.assertTrue({"▷今天", "▷未来七天"} <= text)
        self.assertTrue({"▷截止", "▷待办", "私人事项"}.isdisjoint(text))

    @patch.dict(os.environ, {"WEATHER_KEY": "test", "WEATHER_HOST": "example.invalid"})
    @patch("kindle_dashboard.sources.weather.request_qweather")
    def test_collects_forecast_aqi_and_alerts(self, request):
        responses = {
            "weather": {"days": [{"forecastStartTime": "2026-11-15T16:00Z",
                       "daytime": {"condition": {"code": "100", "text": "晴"}, "humidity": 0.52},
                       "temperatureMin": {"value": 3}, "temperatureMax": {"value": 14}}]},
            "airquality": {"days": [{"forecastStartTime": "2026-11-15T16:00Z",
                       "indexes": [{"code": "cn-mee", "aqiDisplay": "68"}]}]},
            "weatheralert": {"metadata": {"zeroResult": True}},
        }
        ready = Barrier(3, timeout=5)

        def respond(_endpoint, *, service="weather", **_params):
            ready.wait()
            return responses[service]

        request.side_effect = respond
        weather = collect_weather()
        self.assertEqual(weather.source, "和风天气")
        self.assertEqual(weather.forecast["2026-11-16"]["humidity"], 0.52)
        self.assertEqual(weather.air_quality, {"2026-11-16": "68"})
        self.assertEqual(weather.alerts, [])

    @patch.dict(os.environ, {"WEATHER_KEY": "test", "WEATHER_HOST": "example.invalid"})
    @patch("kindle_dashboard.sources.weather.get_open_meteo_forecast",
           return_value={"2026-11-16": {"low": 3, "high": 14}})
    @patch("kindle_dashboard.sources.weather.request_qweather")
    def test_weather_fallback_keeps_available_alerts(self, request, fallback):
        def respond(_endpoint, *, service="weather", **_params):
            if service == "weatheralert":
                return {"metadata": {"zeroResult": True}}
            raise Timeout

        request.side_effect = respond
        weather = collect_weather()
        fallback.assert_called_once_with()
        self.assertEqual(weather.source, "Open-Meteo")
        self.assertEqual(weather.forecast, fallback.return_value)
        self.assertEqual(weather.air_quality, {})
        self.assertEqual(weather.alerts, [])

    @patch.dict(os.environ, {"ICS_DATA": "", "ICS_FILE": ""})
    def test_two_day_schedule_converts_utc(self):
        fixture = Path(__file__).with_name("example-calendar.ics")
        schedule, _ = get_two_day_schedule(DEMO_NOW, fixture)
        entries_by_day = list(schedule.values())
        self.assertEqual([entries[0]["time"] for entries in entries_by_day], ["09:50", "15:20"])

    def test_recurring_schedule_respects_local_until(self):
        calendar = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Kindle Dashboard//Test Calendar//EN
BEGIN:VEVENT
UID:recurring@example.invalid
DTSTAMP:20261101T000000Z
DTSTART;TZID=Asia/Shanghai:20261115T095000
RRULE:FREQ=DAILY;UNTIL={until}
SUMMARY:示例课程
END:VEVENT
END:VCALENDAR
"""
        for until, expected_times in (
            ("20261116T094900", []),
            ("20261116T095000", ["09:50"]),
            ("20261116", ["09:50"]),
            ("20261116T015000Z", ["09:50"]),
        ):
            with self.subTest(until=until):
                with patch.dict(os.environ, {"ICS_DATA": calendar.format(until=until)}):
                    schedule, status = get_two_day_schedule(DEMO_NOW)
                self.assertEqual(status, "暂无日程")
                self.assertEqual([[entry["time"] for entry in day] for day in schedule.values()],
                                 [expected_times, []])

    def test_recurring_schedule_replaces_moved_and_cancelled_instances(self):
        calendar = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Kindle Dashboard//Test Calendar//EN
BEGIN:VEVENT
UID:recurring@example.invalid
DTSTAMP:20261101T000000Z
DTSTART;TZID=Asia/Shanghai:20261115T090000
RRULE:FREQ=DAILY;COUNT=4
SUMMARY:示例课程
LOCATION:示例教室
END:VEVENT
BEGIN:VEVENT
UID:recurring@example.invalid
DTSTAMP:20261101T000000Z
RECURRENCE-ID:20261116T010000Z
DTSTART;TZID=Asia/Shanghai:20261116T120000
END:VEVENT
BEGIN:VEVENT
UID:recurring@example.invalid
DTSTAMP:20261101T000000Z
RECURRENCE-ID;TZID=Asia/Shanghai:20261117T090000
STATUS:CANCELLED
END:VEVENT
BEGIN:VEVENT
UID:recurring@example.invalid
DTSTAMP:20261101T000000Z
RECURRENCE-ID;TZID=Asia/Shanghai:20261118T090000
DTSTART;TZID=Asia/Shanghai:20261117T150000
SUMMARY:调入的课
END:VEVENT
END:VCALENDAR
"""
        with patch.dict(os.environ, {"ICS_DATA": calendar}):
            schedule, status = get_two_day_schedule(DEMO_NOW)
        self.assertEqual(status, "暂无日程")
        self.assertEqual(list(schedule.values()), [
            [{"time": "12:00", "name": "示例课程", "place": "示例教室"}],
            [{"time": "15:00", "name": "调入的课", "place": "示例教室"}],
        ])

    @patch("builtins.print")
    def test_bad_tasks_are_skipped_individually(self, log):
        settings = {"tasks": [
            {"title": "错误日期", "due": "bad-date"},
            {"due": "2026-11-16"},
            {"title": "有效截止", "due": "2026-11-16T15:00"},
            {"title": "有效待办"},
            {"title": "已完成", "done": True},
        ]}
        deadlines, todos = dashboard_tasks(settings, DEMO_NOW.date())
        self.assertEqual([title for _, title in deadlines], ["有效截止"])
        self.assertEqual(todos, ["有效待办"])
        self.assertIn("第 1 项的 due", log.call_args_list[0].args[0])
        self.assertIn("第 2 项的 title", log.call_args_list[1].args[0])

    def test_json_tasks_override_old_sources_even_when_empty(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "tasks.local.json"
            old_path = root / "tasks.local.md"
            settings = {"tasks_file": str(old_path), "tasks": [{"title": "旧清单"}]}
            self.assertEqual(task_file(settings), path)
            self.assertEqual(dashboard_tasks(settings, DEMO_NOW.date(), path=path),
                             ([], ["旧清单"]))
            original = (
                "# 清单\n"
                "- [ ] 2026-11-19 18:00 | 截止事项\n"
                "- [ ] 整理资料 | 保留竖线\n"
                "- [x] 已完成\n"
            )
            old_path.write_text(original, encoding="utf-8")
            store = TaskList(path, settings)
            snapshot = store.snapshot()
            self.assertTrue(snapshot["tasks"][2]["done"])
            self.assertTrue(store.update({
                "action": "add", "revision": snapshot["revision"],
                "title": "2026-11-19 | 保留标题", "due": None,
            }))
            self.assertFalse(store.update({"action": "delete", "id": 0,
                                           "revision": snapshot["revision"]}))
            deadlines, todos = dashboard_tasks(settings, DEMO_NOW.date(), path=path)
            self.assertEqual([(due.isoformat(), title) for due, title in deadlines],
                             [("2026-11-19T18:00:00+08:00", "截止事项")])
            self.assertEqual(todos, ["整理资料 | 保留竖线", "2026-11-19 | 保留标题"])
            self.assertEqual(old_path.read_text(encoding="utf-8"), original)
            path.write_text("[]", encoding="utf-8")
            self.assertEqual(dashboard_tasks(settings, DEMO_NOW.date(), path=path), ([], []))

    @patch("kindle_dashboard.sources.timetable.get_two_day_schedule", return_value=({}, "暂无日程"))
    def test_dashboard_reads_configured_task_file(self, _schedule):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tasks.local.json").write_text('[{"title":"默认清单"}]', encoding="utf-8")
            (root / "private").mkdir()
            (root / "private" / "tasks.json").write_text('[{"title":"指定清单"}]', encoding="utf-8")
            with patch("kindle_dashboard.tasks.ROOT", root), patch(
                "kindle_dashboard.application.load_settings",
                return_value={"tasks_file": "private/tasks.json"},
            ):
                widgets = build_dashboard(demo=False, offline=True, hide_personal=False)["widgets"]
            self.assertEqual([widget["content"] for widget in widgets if widget.get("type") == "todo"],
                             ["指定清单"])


if __name__ == "__main__":
    unittest.main()
