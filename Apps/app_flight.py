# Made by FlyingCoco-Offical as an offical app for SmartMotor-OS. For any issues make a Github issue.

# --- APP CONFIGURATION ---
ENABLE_APP = True
APP_ORDER = 1  # 1 shows first, 2 shows second, etc.

# Mode: "AIRPORT" or "MANUAL"
TRACK_MODE = "AIRPORT"
AIRPORT_CODE = "KLAX"

MANUAL_LAT, MANUAL_LON = 34.2068, -118.2000
LAT_SPAN = 0.25
LON_SPAN = 0.25

OPENSKY_ROUTE_URL = "https://opensky-network.org/api/routes?callsign="

import time
import urequests
import math

APP_NAME = "Live Flight Tracking"

def get_airport_location(icao_code):
    code = icao_code.strip().upper()
    try:
        res = urequests.get(f"https://api.vatsim.net/v2/atc/airport/{code}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            res.close()
            if "latitude" in data and "longitude" in data:
                return float(data["latitude"]), float(data["longitude"]), code
    except Exception:
        pass
    return None, None, None

def resolve_bounds():
    lat, lon, label = None, None, "Manual"
    if TRACK_MODE == "AIRPORT":
        lat, lon, label = get_airport_location(AIRPORT_CODE)

    if lat is None or lon is None:
        lat, lon = MANUAL_LAT, MANUAL_LON
        label = "Manual Coords" if TRACK_MODE == "MANUAL" else "Fallback Mode"

    lamin, lamax = lat - LAT_SPAN, lat + LAT_SPAN
    lomin, lomax = lon - LON_SPAN, lon + LON_SPAN

    url = f"https://opensky-network.org/api/states/all?lamin={lamin}&lamax={lamax}&lomin={lomin}&lomax={lomax}"
    return lat, lon, label, url

def calc_dist(lat1, lon1, lat2, lon2):
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def get_route(callsign):
    if not callsign or callsign == "UNKNOWN":
        return "N/A", "N/A"
    try:
        res = urequests.get(OPENSKY_ROUTE_URL + callsign, timeout=5)
        if res.status_code == 200:
            data = res.json()
            res.close()
            route = data.get("route", [])
            if len(route) >= 2:
                return route[0], route[1]
            elif len(route) == 1:
                return route[0], "N/A"
        res.close()
    except Exception:
        pass
    return "N/A", "N/A"

def run(sys):
    if not sys["ensure_wifi"]():
        sys["display"].fill(0)
        sys["display"].text("WiFi Failed!", 0, 20)
        sys["display"].show()
        time.sleep(2)
        return

    sys["display"].fill(0)
    sys["display"].text("Fetching Airport...", 0, 20)
    sys["display"].show()

    home_lat, home_lon, mode_label, opensky_url = resolve_bounds()

    while True:
        if sys["check_exit"](): return
        
        sys["display"].fill(0)
        sys["display"].text("Scanning Sky...", 0, 10)
        sys["display"].text(f"Zone:{mode_label[:10]}", 0, 25)
        sys["display"].text("Hold BigBtn Exit", 0, 48)
        sys["display"].show()

        try:
            res = urequests.get(opensky_url, timeout=10)
            data = res.json()
            res.close()
            states = data.get("states")

            if states and len(states) > 0:
                closest_plane = None
                closest_dist = 9999

                for p in states:
                    p_lon, p_lat = p[5], p[6]
                    if p_lat is not None and p_lon is not None:
                        d = calc_dist(home_lat, home_lon, p_lat, p_lon)
                        if d < closest_dist:
                            closest_dist = d
                            closest_plane = p

                if closest_plane:
                    callsign = closest_plane[1].strip() if closest_plane[1] else "UNKNOWN"
                    alt_ft = int(closest_plane[7] * 3.28084) if closest_plane[7] else 0
                    spd_mph = int(closest_plane[9] * 2.23694) if closest_plane[9] else 0
                    origin, dest = get_route(callsign)

                    start_t = time.time()
                    while time.time() - start_t < 30:
                        if sys["check_exit"](): return
                        
                        sys["display"].fill(0)
                        sys["display"].text(f"FLT:{callsign[:7]} {int(closest_dist)}mi", 0, 0)
                        sys["display"].hline(0, 10, 128, 1)
                        sys["display"].text(f"RTE: {origin}->{dest}", 0, 15)
                        sys["display"].text(f"ALT: {alt_ft:,} ft", 0, 28)
                        sys["display"].text(f"SPD: {spd_mph} mph", 0, 40)
                        sys["display"].hline(0, 52, 128, 1)
                        sys["display"].text("Hold BigBtn Exit", 0, 55)
                        sys["display"].show()
                        time.sleep(0.2)
        except Exception:
            pass

        for _ in range(20):
            if sys["check_exit"](): return
            time.sleep(0.25)

                return route[0], route[1]
            elif len(route) == 1:
                return route[0], "N/A"
        res.close()
    except Exception:
        pass
    return "N/A", "N/A"

def run(sys):
    if not sys["ensure_wifi"]():
        sys["display"].fill(0)
        sys["display"].text("WiFi Failed!", 0, 20)
        sys["display"].show()
        time.sleep(2)
        return

    sys["display"].fill(0)
    sys["display"].text("Fetching Airport...", 0, 20)
    sys["display"].show()

    home_lat, home_lon, mode_label, opensky_url = resolve_bounds()

    while True:
        if sys["check_exit"](): return
        
        sys["display"].fill(0)
        sys["display"].text("Scanning Sky...", 0, 10)
        sys["display"].text(f"Zone:{mode_label[:10]}", 0, 25)
        sys["display"].text("Hold BigBtn: Exit", 0, 48)
        sys["display"].show()

        try:
            res = urequests.get(opensky_url, timeout=10)
            data = res.json()
            res.close()
            states = data.get("states")

            if states and len(states) > 0:
                closest_plane = None
                closest_dist = 9999

                for p in states:
                    p_lon, p_lat = p[5], p[6]
                    if p_lat is not None and p_lon is not None:
                        d = calc_dist(home_lat, home_lon, p_lat, p_lon)
                        if d < closest_dist:
                            closest_dist = d
                            closest_plane = p

                if closest_plane:
                    callsign = closest_plane[1].strip() if closest_plane[1] else "UNKNOWN"
                    alt_ft = int(closest_plane[7] * 3.28084) if closest_plane[7] else 0
                    spd_mph = int(closest_plane[9] * 2.23694) if closest_plane[9] else 0
                    origin, dest = get_route(callsign)

                    start_t = time.time()
                    while time.time() - start_t < 30:
                        if sys["check_exit"](): return
                        
                        sys["display"].fill(0)
                        sys["display"].text(f"FLT:{callsign[:7]} {int(closest_dist)}mi", 0, 0)
                        sys["display"].hline(0, 10, 128, 1)
                        sys["display"].text(f"RTE: {origin}->{dest}", 0, 15)
                        sys["display"].text(f"ALT: {alt_ft:,} ft", 0, 28)
                        sys["display"].text(f"SPD: {spd_mph} mph", 0, 40)
                        sys["display"].hline(0, 52, 128, 1)
                        sys["display"].text("Hold BigBtn Exit", 0, 55)
                        sys["display"].show()
                        time.sleep(0.2)
        except Exception:
            pass

        for _ in range(20):
            if sys["check_exit"](): return
            time.sleep(0.25)
