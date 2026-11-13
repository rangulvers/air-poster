# air-poster

Shows nearby air traffic on a jailbroken Kindle Paperwhite 2 (758x1024, firmware 5.12.2.2).
The server renders a PNG; the Kindle only fetches and displays it.

## Server

```bash
pip install pillow
HOME_LAT=52.52 HOME_LON=13.40 RANGE_NM=30 python3 server/airposter.py
# optional: AIRCRAFT_URL=http://<receiver>/tar1090/data/aircraft.json
```

Open `http://<server>:8080/dashboard.png` to check it. Without `AIRCRAFT_URL`,
the airplanes.live point API is used.

## Kindle

1. Edit `SERVER_URL` in `kindle/airposter/bin/config.sh`.
2. Copy `kindle/airposter` to `extensions/airposter` on the Kindle (USB).
3. Open KUAL > Air Poster > "Show one frame (test)" first, then "Start dashboard".

Scripts draw with `eips -g`. If the PNG doesn't display correctly, switch to FBInk.
