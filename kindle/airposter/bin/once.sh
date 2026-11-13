#!/bin/sh
# Fetch one frame and draw it. Use this first to check that eips can show the PNG.
. "$(dirname "$0")/config.sh"

wget -q -O "$IMG" "$SERVER_URL" || exit 1
eips -c
eips -g "$IMG"
