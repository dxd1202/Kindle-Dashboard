"""Command line entry point for the dashboard generator."""

import argparse
from pathlib import Path

from .application import build_dashboard
from .config import ROOT
from .render import add_system_fonts, render


def load_local_environment():
    if (ROOT / ".env").is_file():
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, help="看板布局 JSON")
    parser.add_argument("--offline", action="store_true", help="跳过实时数据采集")
    parser.add_argument("--demo", action="store_true", help="用示例数据预览新版看板")
    parser.add_argument("--hide-timetable", action="store_true", help="隐藏日程、截止和待办，用于公开发布")
    parser.add_argument("--output", type=Path, help="PNG 输出路径，默认 build/output.png")
    parser.add_argument("--edit-tasks", action="store_true", help="在浏览器中管理任务和日程")
    args = parser.parse_args()
    if args.edit_tasks:
        if args.config or args.demo or args.offline or args.hide_timetable or args.output:
            parser.error("--edit-tasks 请单独使用")
        from .task_editor import run_editor

        load_local_environment()
        run_editor()
        return
    if args.demo and args.config:
        parser.error("--demo 不能与 --config 同时使用")

    if args.config:
        from .legacy import load_layout

        config = load_layout(args.config, offline=args.offline, hide_personal=args.hide_timetable)
    else:
        if not args.demo and not args.offline:
            load_local_environment()
        config = build_dashboard(demo=args.demo, offline=args.offline, hide_personal=args.hide_timetable)
        add_system_fonts(config)

    render(config, output=args.output)
