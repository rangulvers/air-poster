#!/bin/sh
. "$(dirname "$0")/config.sh"

[ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null
rm -f "$PIDFILE"
lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null
eips -c
