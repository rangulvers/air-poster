#!/usr/bin/env python3
"""Render nearby air traffic as a 758x1024 grayscale PNG for a Kindle Paperwhite 2.

Serves the image at /dashboard.png. Configuration is via environment variables:

  HOME_LAT, HOME_LON   your position (required)
  RANGE_NM             radar radius in nautical miles (default 30)
  AIRCRAFT_URL         readsb/tar1090 aircraft.json URL, e.g.
                       http://192.168.1.10/tar1090/data/aircraft.json
                       If unset, the airplanes.live point API is used.
  PORT                 HTTP port (default 8080)
  CACHE_SECONDS        minimum seconds between upstream fetches (default 20)

Run `airposter.py --once out.png` to render a single image and exit.
"""
import json
import math
import os
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

W, H = 758, 1024
MAP_H = 758
FONT_DIR = "/usr/share/fonts/truetype/dejavu/"

HOME_LAT = float(os.environ.get("HOME_LAT", "0"))
HOME_LON = float(os.environ.get("HOME_LON", "0"))
RANGE_NM = float(os.environ.get("RANGE_NM", "30"))
AIRCRAFT_URL = os.environ.get("AIRCRAFT_URL", "")
PORT = int(os.environ.get("PORT", "8080"))
CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", "20"))


def font(size, bold=False):
    name = "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"
    try:
        return ImageFont.truetype(FONT_DIR + name, size)
    except OSError:
        return ImageFont.load_default()


def fetch_aircraft():
    url = AIRCRAFT_URL or (
        f"https://api.airplanes.live/v2/point/{HOME_LAT}/{HOME_LON}/{int(RANGE_NM)}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "air-poster"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.load(resp)
    raw = data.get("ac") or data.get("aircraft") or []
    planes = []
    for a in raw:
        lat, lon = a.get("lat"), a.get("lon")
        if lat is None or lon is None:
            continue
        dx = (lon - HOME_LON) * 60 * math.cos(math.radians(HOME_LAT))
        dy = (lat - HOME_LAT) * 60
        dist = math.hypot(dx, dy)
        if dist > RANGE_NM:
            continue
        alt = a.get("alt_baro")
        planes.append({
            "call": (a.get("flight") or a.get("r") or a.get("hex") or "?").strip(),
            "type": a.get("t") or "",
            "alt": alt if isinstance(alt, (int, float)) else 0 if alt == "ground" else None,
            "gs": a.get("gs"),
            "track": a.get("track"),
            "dx": dx,
            "dy": dy,
            "dist": dist,
        })
    planes.sort(key=lambda p: p["dist"])
    return planes


def render(planes):
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, MAP_H // 2
    radius = MAP_H // 2 - 28
    scale = radius / RANGE_NM

    # range rings and crosshair
    for frac in (1 / 3, 2 / 3, 1):
        r = radius * frac
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=170 if frac < 1 else 0)
        d.text((cx + 4, cy - r - 12), f"{RANGE_NM * frac:.0f}nm", font=font(11), fill=110)
    d.line([cx - radius, cy, cx + radius, cy], fill=200)
    d.line([cx, cy - radius, cx, cy + radius], fill=200)
    d.text((cx - 4, cy - radius - 20), "N", font=font(14, True), fill=0)
    d.rectangle([cx - 3, cy - 3, cx + 3, cy + 3], fill=0)  # home

    f = font(13, True)
    for p in planes:
        x = cx + p["dx"] * scale
        y = cy - p["dy"] * scale
        if p["track"] is not None:
            t = math.radians(p["track"])
            d.line([x, y, x + 14 * math.sin(t), y - 14 * math.cos(t)], fill=0, width=2)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=0)
        d.text((x + 7, y - 7), p["call"], font=f, fill=0)

    # table of the closest aircraft
    d.line([0, MAP_H + 4, W, MAP_H + 4], fill=0, width=2)
    d.text((12, MAP_H + 10), "CALLSIGN   TYPE   ALT(ft)  GS(kt)  DIST(nm)",
           font=font(15, True), fill=0)
    row = font(16)
    y = MAP_H + 34
    for p in planes[:8]:
        alt = "-" if p["alt"] is None else f"{int(p['alt'])}"
        gs = "-" if p["gs"] is None else f"{int(p['gs'])}"
        line = f"{p['call']:<10} {p['type']:<6} {alt:>7}  {gs:>6}  {p['dist']:>8.1f}"
        d.text((12, y), line, font=row, fill=0)
        y += 24
    stamp = time.strftime("%H:%M:%S")
    d.text((W - 150, H - 20), f"{len(planes)} in range  {stamp}", font=font(12), fill=90)
    return img


_cache = {"t": 0.0, "png": b""}
_lock = threading.Lock()


def current_png():
    with _lock:
        if time.time() - _cache["t"] > CACHE_SECONDS:
            try:
                planes = fetch_aircraft()
            except Exception as e:  # keep serving something on upstream failure
                print("fetch failed:", e, file=sys.stderr)
                planes = []
            buf = BytesIO()
            render(planes).save(buf, "PNG")
            _cache.update(t=time.time(), png=buf.getvalue())
        return _cache["png"]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] != "/dashboard.png":
            self.send_error(404)
            return
        body = current_png()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--once":
        with open(sys.argv[2], "wb") as fh:
            fh.write(current_png())
    else:
        print(f"serving on :{PORT}/dashboard.png")
        ThreadingHTTPServer(("", PORT), Handler).serve_forever()
