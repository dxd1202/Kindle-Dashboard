#!/bin/sh
dir=$(dirname "$0")
nohup setsid /bin/sh "$dir/dash.sh" </dev/null >/dev/null 2>&1 &
