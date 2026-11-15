#!/bin/sh
dir=$(dirname "$0")
lock=/tmp/kindle-dashboard.lock

if ! mkdir "$lock" 2>/dev/null; then
    exit 0
fi
printf '%s\n' "$$" > "$lock/pid"
previous_screensaver=
restore_framework=no
exit_watchers=
wait_pid=

cleanup() {
    if [ -n "$wait_pid" ]; then kill "$wait_pid" 2>/dev/null; fi
    for watcher in $exit_watchers; do kill "$watcher" 2>/dev/null; done
    if [ "$restore_framework" = yes ]; then
        case "$(initctl status lab126_gui 2>/dev/null)" in
            'lab126_gui start/running'*) ;;
            *)
                log "Restoring the Kindle interface."
                (cd / && initctl start lab126_gui) || log "Could not restart the Kindle interface"
                ;;
        esac
    fi
    if [ -n "$previous_screensaver" ]; then
        lipc-set-prop com.lab126.powerd preventScreenSaver "$previous_screensaver"
    fi
    rm -f "$lock/pid"
    rmdir "$lock"
}
trap cleanup EXIT
trap 'exit 0' HUP INT TERM

mkdir -p "$dir/logs" || exit 1
log_file="$dir/logs/dash.log"
if [ -f "$log_file" ]; then
    tail -n 1000 "$log_file" > "$log_file.tmp" && mv "$log_file.tmp" "$log_file"
fi
exec >> "$log_file" 2>&1

[ ! -f "$dir/local/env.sh" ] || . "$dir/local/env.sh"
schedule=${REFRESH_SCHEDULE:-"10,40 0,7-23 * * *"}
timezone=${TIMEZONE:-Asia/Shanghai}
image="$dir/dash.png"

log() {
    printf '%s : %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

previous_screensaver=$(lipc-get-prop com.lab126.powerd preventScreenSaver 2>/dev/null)
case "$previous_screensaver" in 0|1) ;; *) previous_screensaver=0 ;; esac
if ! lipc-set-prop com.lab126.powerd preventScreenSaver 1; then
    log "Could not prevent the Kindle screensaver"
fi

case "$(initctl status lab126_gui 2>/dev/null)" in
    'lab126_gui start/running'*) ;;
    *) log "Could not identify a running Kindle interface"; exit 1 ;;
esac

# The KUAL menu is unavailable while the native interface is stopped.
# Two independent exit triggers: the hardware key, or a USB data connection.
dashboard_pid=$$
watch_exit_event() (
    event=$1
    lipc-wait-event -s 0 com.lab126.hal "$event" &
    listener=$!
    trap 'kill "$listener" 2>/dev/null; exit 0' HUP INT TERM
    if wait "$listener"; then
        log "Exiting dashboard after $event."
    else
        log "Could not listen for $event; exiting dashboard."
    fi
    kill -TERM "$dashboard_pid" 2>/dev/null
)
watch_exit_event powerButtonPressed &
exit_watchers=$!
watch_exit_event usbConfigured &
exit_watchers="$exit_watchers $!"

restore_framework=yes
if ! initctl stop lab126_gui; then
    log "Could not stop the Kindle interface"
    exit 1
fi
# Let the firmware finish its final screen redraw before drawing the dashboard.
sleep 2

wifi_state() {
    wpa_cli -i wlan0 status 2>/dev/null | sed -n 's/^wpa_state=//p'
}

reconnect_wifi() {
    radio=$(lipc-get-prop com.lab126.cmd wirelessEnable 2>/dev/null)
    if [ "$radio" = 0 ]; then
        log "Wi-Fi is switched off; enable it in Kindle settings."
        return 1
    fi
    log "Wi-Fi disconnected; requesting reassociation with saved networks."
    if [ "$(wpa_cli -i wlan0 reassociate 2>/dev/null)" != OK ]; then
        log "Kindle did not accept the Wi-Fi reassociation request."
        return 1
    fi
    for attempt in 1 2 3 4 5 6 7 8 9 10; do
        sleep 3
        if [ "$(wifi_state)" = COMPLETED ]; then
            log "Wi-Fi reconnected."
            return 0
        fi
    done
    log "Wi-Fi did not reconnect within 30 seconds."
    return 1
}

while :; do
    retry_wifi=no
    if /bin/sh "$dir/local/fetch-dashboard.sh" "$image"; then
        log "Dashboard image downloaded"
        /usr/sbin/eips -f -g "$image" || log "Could not draw dashboard image"
    else
        state=$(wifi_state)
        case "$state" in
            COMPLETED|'')
                log "Download failed (Wi-Fi state: ${state:-unknown}); checking again at the next scheduled refresh."
                warning="Download failed - keeping last image"
                ;;
            *)
                retry_wifi=yes
                if reconnect_wifi; then
                    retry_wifi=no
                    if /bin/sh "$dir/local/fetch-dashboard.sh" "$image"; then
                        log "Dashboard image downloaded after reconnecting"
                        /usr/sbin/eips -f -g "$image" || log "Could not draw dashboard image"
                        warning=
                    else
                        log "Download failed after reconnecting."
                        warning="Download failed - keeping last image"
                    fi
                else
                    warning="Wi-Fi offline - retrying"
                fi
                ;;
        esac
        if [ -n "$warning" ]; then
            if [ -s "$image" ]; then /usr/sbin/eips -f -g "$image"; fi
            /usr/sbin/eips 1 1 "$warning"
        fi
    fi

    delay=$("$dir/next-wakeup" --schedule="$schedule" --timezone="$timezone" 2>/dev/null)
    case "$delay" in ''|*[!0-9]*) delay=1800 ;; esac
    if ! [ "$delay" -ge 30 ] 2>/dev/null; then delay=30; fi
    if [ "$retry_wifi" = yes ] && [ "$delay" -gt 60 ]; then delay=60; fi
    log "Next download in ${delay}s"
    sleep "$delay" &
    wait_pid=$!
    wait "$wait_pid"
    wait_pid=
done
