#!/bin/sh
pid=$(cat /tmp/kindle-dashboard.lock/pid 2>/dev/null)
case "$pid" in
    ''|0|1|*[!0-9]*) exit 0 ;;
esac
command=$(tr '\000' ' ' < "/proc/$pid/cmdline" 2>/dev/null)
case "$command" in
    *" /mnt/us/dashboard/dash.sh "*) ;;
    *) exit 0 ;;
esac
kill "$pid" 2>/dev/null
