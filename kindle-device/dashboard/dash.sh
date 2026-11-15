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
restore_wifi=no

cleanup() {
    if [ -n "$wait_pid" ]; then kill "$wait_pid" 2>/dev/null; fi
    for watcher in $exit_watchers; do kill "$watcher" 2>/dev/null; done
    if [ "$restore_wifi" = yes ]; then
        lipc-set-prop com.lab126.cmd wirelessEnable 1 || log "Could not restore Wi-Fi."
    fi
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

wait_for_wifi() {
    unknown_checks=0
    for attempt in 1 2 3 4 5 6 7 8 9 10; do
        sleep 3
        case "$(wifi_state)" in
            COMPLETED)
                log "Wi-Fi associated; checking the image URL."
                return 0
                ;;
            '')
                unknown_checks=$((unknown_checks + 1))
                if [ "$unknown_checks" -ge 3 ]; then
                    log "Wi-Fi status unavailable; testing the image URL directly."
                    return 0
                fi
                ;;
            *) unknown_checks=0 ;;
        esac
    done
    log "Wi-Fi did not report association after 10 checks."
    return 1
}

reconnect_wifi() {
    log "Requesting Wi-Fi reassociation with saved networks."
    if [ "$(wpa_cli -i wlan0 reassociate 2>/dev/null)" != OK ]; then
        log "Kindle did not accept the Wi-Fi reassociation request."
        return 1
    fi
    wait_for_wifi
}

reset_wifi() {
    if [ "$(lipc-get-prop com.lab126.cmd wirelessEnable 2>/dev/null)" != 1 ]; then
        return 1
    fi
    log "Download still unavailable; restarting Wi-Fi."
    restore_wifi=yes
    if ! lipc-set-prop com.lab126.cmd wirelessEnable 0; then
        log "Could not turn Wi-Fi off for recovery."
        return 1
    fi
    sleep 3
    if ! lipc-set-prop com.lab126.cmd wirelessEnable 1; then
        log "Could not turn Wi-Fi back on."
        return 1
    fi
    restore_wifi=no
    wait_for_wifi
}

network_failures=0
next_wifi_reset=0
while :; do
    /bin/sh "$dir/local/fetch-dashboard.sh" "$image"
    fetch_status=$?
    if [ "$fetch_status" -ne 0 ]; then
        state=$(wifi_state)
        radio=$(lipc-get-prop com.lab126.cmd wirelessEnable 2>/dev/null)
        log "Download failed (exit $fetch_status, Wi-Fi state: ${state:-unknown}, radio: ${radio:-unknown})."
        if [ "$restore_wifi" = yes ] && lipc-set-prop com.lab126.cmd wirelessEnable 1; then
            restore_wifi=no
            radio=1
        fi
        if [ "$radio" = 0 ]; then
            log "Wi-Fi is switched off; enable it in Kindle settings."
        elif [ "$fetch_status" -eq 1 ]; then
            network_failures=$((network_failures + 1))
            if [ "$network_failures" -eq 1 ] && [ "$state" = COMPLETED ]; then
                next_wifi_reset=2
            fi
            if reconnect_wifi; then
                /bin/sh "$dir/local/fetch-dashboard.sh" "$image"
                fetch_status=$?
            fi
            # Keep retrying downloads between radio resets.
            if [ "$fetch_status" -eq 1 ] && [ "$network_failures" -ge "$next_wifi_reset" ]; then
                next_wifi_reset=$((network_failures + 3))
                if reset_wifi; then
                    /bin/sh "$dir/local/fetch-dashboard.sh" "$image"
                    fetch_status=$?
                fi
            fi
        fi
    fi

    if [ "$fetch_status" -ne 1 ] || [ "${radio:-}" = 0 ]; then
        network_failures=0
        next_wifi_reset=0
    fi
    if [ "$fetch_status" -eq 0 ]; then
        log "Dashboard image downloaded"
        /usr/sbin/eips -f -g "$image" || log "Could not draw dashboard image"
    else
        if [ -s "$image" ]; then /usr/sbin/eips -f -g "$image"; fi
        /usr/sbin/eips 1 1 "Download failed - retrying"
    fi

    delay=$("$dir/next-wakeup" --schedule="$schedule" --timezone="$timezone" 2>/dev/null)
    case "$delay" in ''|*[!0-9]*) delay=1800 ;; esac
    if ! [ "$delay" -ge 30 ] 2>/dev/null; then delay=30; fi
    if [ "$fetch_status" -eq 1 ] && [ "${radio:-}" != 0 ] && [ "$delay" -gt 30 ]; then
        delay=30
    elif [ "$fetch_status" -ne 0 ] && [ "$delay" -gt 60 ]; then
        delay=60
    fi
    log "Next download in ${delay}s"
    sleep "$delay" &
    wait_pid=$!
    wait "$wait_pid"
    wait_pid=
done
