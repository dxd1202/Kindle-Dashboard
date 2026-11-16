"""Command line entry point for the dashboard generator."""

import argparse
from pathlib import Path

from .application import collect_dashboard
from .config import ROOT
from .render import render


def load_local_environment():
    if (ROOT / ".env").is_file():
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="跳过实时数据采集")
    parser.add_argument("--demo", action="store_true", help="用示例数据预览看板")
    parser.add_argument("--hide-timetable", action="store_true", help="隐藏日程、截止和待办，用于公开发布")
    parser.add_argument("--output", type=Path, help="PNG 输出路径，默认 build/output.png")
    parser.add_argument("--edit-tasks", action="store_true", help="在浏览器中管理任务和日程")
    parser.add_argument("--web-output", type=Path, help="同时生成手机版网页到指定目录")
    parser.add_argument("--web-data", choices=("demo", "weather", "personal"), default="demo",
                        help="手机版数据范围，默认仅发布示例")
    parser.add_argument("--web-locations", action="store_true", help="在个人版中显示日程地点")
    args = parser.parse_args()
    if args.edit_tasks:
        if args.demo or args.offline or args.hide_timetable or args.output or args.web_output:
            parser.error("--edit-tasks 请单独使用")
        from .task_editor import run_editor

        load_local_environment()
        run_editor()
        return
    if not args.demo and not args.offline:
        load_local_environment()
    if not args.web_output and (args.web_data != "demo" or args.web_locations):
        parser.error("--web-data 和 --web-locations 需要 --web-output")
    if args.web_locations and args.web_data != "personal":
        parser.error("--web-locations 需要 --web-data personal")
    snapshot = collect_dashboard(demo=args.demo, offline=args.offline, hide_personal=args.hide_timetable,
                                 include_end=bool(args.web_output) and args.web_data == "personal")
    render(snapshot.layout(), output=args.output)
    if args.web_output:
        from .mobile import export_mobile

        mobile = snapshot
        if args.web_data == "demo" and (not snapshot.demo or snapshot.hide_personal):
            mobile = collect_dashboard(demo=True, offline=True, hide_personal=False)
        export_mobile(mobile, args.web_output, mode=args.web_data, show_locations=args.web_locations)
