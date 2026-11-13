#!/bin/sh
# Loop: fetch the rendered PNG and draw it with eips. The Kindle UI keeps running
# underneath, so this version is for testing and for a Kindle on the charger.
DIR="$(dirname "$0")"
. "$DIR/config.sh"

[ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null

(
  # keep the screen from sleeping or showing the screensaver while we run
  lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
  while true; do
    if wget -q -O "$IMG.tmp" "$SERVER_URL"; then
      mv "$IMG.tmp" "$IMG"
      eips -g "$IMG"
    fi
    sleep "$REFRESH_SECONDS"
  done
) >/dev/null 2>&1 &
echo $! > "$PIDFILE"
