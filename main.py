import network
import time
import urequests
import math
import ntptime
from machine import Pin, I2C, ADC
import ssd1306

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# --= WIFI CONFIG =--- (Required for Flight Tracking)
WIFI_SSID = "YOUR_WIFI_NAME" # WiFi Name     (e.g., "Spectrum_Setup 00")
WIFI_PASS = "YOUR_WIFI_PASSWORD"       # WiFi Password (e.g., "password1234")

# --= FLIGHT TRACKING CONFIG =--
TRACK_MODE = "AIRPORT"  # Options: "AIRPORT" (Primary) or "MANUAL" (Fallback option)

# - Tracking Mode: AIRPORT -
AIRPORT_CODE = "KLAX"   # Change to any K-code (e.g., KBUR, KJFK, KORD)

# - Tracking Mode: MANUAL -
MANUAL_LAT, MANUAL_LON = 34.2068, -118.2000

# Search area radius (~0.25° ≈ 15-20 miles around point)
LAT_SPAN = 0.25
LON_SPAN = 0.25

# --= CLOCK FORMAT CONFIG =--
USE_24HR_TIME = False  # True == 24-hour (e.g., 14:30:00), False == 12-hour (e.g., 02:30:00PM)
DATE_FORMAT = False     # True == DD/MM/YYYY, False == MM/DD/YYYY

# ==============================================================================
# BOARD PINS & HARDWARE SETUP
# ==============================================================================
K1_PIN = 10          # K1 Side Button -> MOVE DOWN
K2_PIN = 8           # K2 Side Button -> MOVE UP
SELECT_PIN = 9       # Big White Front Button -> SELECT / EXIT
BATTERY_ADC_PIN = 0  # Tufts CEEO Board uses Pin 0 (A0)

btn_k1 = Pin(K1_PIN, Pin.IN, Pin.PULL_UP)
btn_k2 = Pin(K2_PIN, Pin.IN, Pin.PULL_UP)
btn_select = Pin(SELECT_PIN, Pin.IN, Pin.PULL_UP)

# Fallback pins for K1
K1_ALT_PINS = [4, 5]
alt_k1_objs = [Pin(p, Pin.IN, Pin.PULL_UP) for p in K1_ALT_PINS]

# Battery ADC
batt_adc = ADC(Pin(BATTERY_ADC_PIN))
batt_adc.atten(ADC.ATTN_11DB)

# Display Setup
i2c = I2C(0, scl=Pin(7), sda=Pin(6))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# --- SYSTEM GLOBALS & URLS ---
OPENSKY_ROUTE_URL = "https://opensky-network.org/api/routes?callsign="
IP_GEO_URL = "http://ip-api.com/json/?fields=timezone,offset"

APPS = [
    "Live Flight Tracking",
    "Digital Clock",
    "System Info"
]

HOME_LAT = MANUAL_LAT
HOME_LON = MANUAL_LON

# ==============================================================================
# BUTTON HELPERS
# ==============================================================================
def is_pressed(btn_pin):
    return btn_pin.value() == 0

def is_k1_pressed():
    if is_pressed(btn_k1):
        return True
    for alt_btn in alt_k1_objs:
        if alt_btn.value() == 0:
            return True
    return False

def check_exit_hold():
    if is_pressed(btn_select):
        press_start = time.time()
        while is_pressed(btn_select):
            held_dur = time.time() - press_start
            display.fill_rect(0, 50, 128, 14, 0)
            display.text(f"EXITING... {int(5 - held_dur)}s", 10, 52, 1)
            display.show()
            
            if held_dur >= 5:
                while is_pressed(btn_select):
                    time.sleep(0.05)
                return True
            time.sleep(0.1)
    return False

def ensure_wifi():
    if WIFI_SSID == "YOUR_WIFI_NAME":
        return False

    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        try:
            wlan.active(False)
            time.sleep(0.3)
        except Exception:
            pass

        wlan.active(True)
        time.sleep(0.2)
        wlan.connect(WIFI_SSID, WIFI_PASS)

        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            
    return wlan.isconnected()

ensure_wifi()

# ==============================================================================
# HARDWARE & API HELPERS
# ==============================================================================
def get_battery_info():
    raw_sum = 0
    for _ in range(15):
        raw_sum += batt_adc.read()
        time.sleep_ms(2)
    raw_avg = raw_sum / 15.0

    pin_voltage = (raw_avg / 4095.0) * 3.3
    batt_volts = pin_voltage * 6.3

    is_charging = batt_volts > 4.25

    if is_charging:
        pct = 100
        batt_text = f"BAT: CHG [CHG] ({batt_volts:.1f}V)"
    elif batt_volts < 3.0:
        pct = 0
        batt_text = f"BAT: Low ({batt_volts:.1f}V)"
    else:
        pct = int(((batt_volts - 3.2) / (4.2 - 3.2)) * 100)
        pct = max(0, min(100, pct))
        batt_text = f"BAT: {pct}% ({batt_volts:.1f}V)"

    return batt_volts, pct, is_charging, batt_text

def get_airport_location(icao_code):
    code = icao_code.strip().upper()
    try:
        res = urequests.get(f"https://api.vatsim.net/v2/atc/airport/{code}")
        if res.status_code == 200:
            data = res.json()
            res.close()
            if "latitude" in data and "longitude" in data:
                return float(data["latitude"]), float(data["longitude"]), code
    except Exception:
        pass
    return None, None, None

def resolve_tracking_bounds():
    lat, lon, label = None, None, "Manual"

    if TRACK_MODE == "AIRPORT":
        lat, lon, label = get_airport_location(AIRPORT_CODE)

    if lat is None or lon is None:
        lat, lon = MANUAL_LAT, MANUAL_LON
        label = "Manual Coords" if TRACK_MODE == "MANUAL" else "Fallback Mode"

    lamin, lamax = lat - LAT_SPAN, lat + LAT_SPAN
    lomin, lomax = lon - LON_SPAN, lon + LON_SPAN

    opensky_url = f"https://opensky-network.org/api/states/all?lamin={lamin}&lamax={lamax}&lomin={lomin}&lomax={lomax}"

    return lat, lon, label, opensky_url

def calculate_distance(lat2, lon2):
    R = 3958.8
    dlat = math.radians(lat2 - HOME_LAT)
    dlon = math.radians(lon2 - HOME_LON)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(HOME_LAT)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def get_flight_route(callsign):
    if not callsign or callsign == "UNKNOWN":
        return "N/A", "N/A"
    try:
        res = urequests.get(OPENSKY_ROUTE_URL + callsign)
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

def get_auto_timezone():
    tz_name = "LOCAL"
    offset_secs = -28800
    try:
        res = urequests.get(IP_GEO_URL)
        if res.status_code == 200:
            data = res.json()
            res.close()
            tz_name = data.get("timezone", "LOCAL").split("/")[-1]
            offset_secs = data.get("offset", -28800)
    except Exception:
        pass
    return tz_name, offset_secs

# ==============================================================================
# APP FUNCTIONS
# ==============================================================================
def run_flight_tracker():
    global HOME_LAT, HOME_LON
    
    if not ensure_wifi():
        display.fill(0)
        display.text("WiFi Failed!", 0, 20)
        display.show()
        time.sleep(2)
        return

    display.fill(0)
    display.text("Fetching Airport...", 0, 20)
    display.show()

    HOME_LAT, HOME_LON, mode_label, opensky_url = resolve_tracking_bounds()

    while True:
        if check_exit_hold(): return
        
        display.fill(0)
        display.text("Scanning Sky...", 0, 10)
        display.text(f"Zone:{mode_label[:10]}", 0, 25)
        display.text("Hold BigBtn Exit", 0, 48)
        display.show()

        try:
            res = urequests.get(opensky_url)
            data = res.json()
            res.close()
            states = data.get("states")

            if states and len(states) > 0:
                closest_plane = None
                closest_dist = 9999

                for p in states:
                    p_lon, p_lat = p[5], p[6]
                    if p_lat is not None and p_lon is not None:
                        d = calculate_distance(p_lat, p_lon)
                        if d < closest_dist:
                            closest_dist = d
                            closest_plane = p

                if closest_plane:
                    callsign = closest_plane[1].strip() if closest_plane[1] else "UNKNOWN"
                    alt_ft = int(closest_plane[7] * 3.28084) if closest_plane[7] else 0
                    spd_mph = int(closest_plane[9] * 2.23694) if closest_plane[9] else 0
                    origin_code, dest_code = get_flight_route(callsign)

                    start_t = time.time()
                    while time.time() - start_t < 30:
                        if check_exit_hold(): return
                        
                        display.fill(0)
                        display.text(f"FLT:{callsign[:7]} {int(closest_dist)}mi", 0, 0)
                        display.hline(0, 10, 128, 1)
                        display.text(f"RTE: {origin_code}->{dest_code}", 0, 15)
                        display.text(f"ALT: {alt_ft:,} ft", 0, 28)
                        display.text(f"SPD: {spd_mph} mph", 0, 40)
                        display.hline(0, 52, 128, 1)
                        display.text("Hold BigBtn Exit", 0, 55)
                        display.show()
                        time.sleep(0.2)
        except Exception:
            pass

        for _ in range(20):
            if check_exit_hold(): return
            time.sleep(0.25)

def run_clock():
    tz_name = "LOCAL"
    offset_secs = -28800

    if ensure_wifi():
        try:
            ntptime.settime()
        except Exception:
            pass

        tz_name, offset_secs = get_auto_timezone()

    while True:
        if check_exit_hold(): return

        utc_secs = time.time()
        local_secs = utc_secs + offset_secs
        tm = time.localtime(local_secs)
        
        year, month, mday, hour, minute, second, weekday, yearday = tm
        
        # --- TIME FORMATTING ---
        if USE_24HR_TIME:
            time_str = f"{hour:02d}:{minute:02d}:{second:02d}"
        else:
            ampm = "AM" if hour < 12 else "PM"
            disp_hour = hour % 12
            if disp_hour == 0:
                disp_hour = 12
            time_str = f"{disp_hour:02d}:{minute:02d}:{second:02d} {ampm}"
            
        # --- DATE FORMATTING ---
        if DATE_FORMAT:
            date_str = f"{mday:02d}/{month:02d}/{year}"  # DD/MM/YYYY
        else:
            date_str = f"{month:02d}/{mday:02d}/{year}"  # MM/DD/YYYY

        display.fill(0)
        display.text(f"TZ: {tz_name[:12]}", 0, 0)
        display.hline(0, 10, 128, 1)
        display.text(time_str, 8 if USE_24HR_TIME else 16, 22)
        display.text(date_str, 24, 36)
        display.hline(0, 50, 128, 1)
        display.text("Hold BigBtn Exit", 0, 54)
        display.show()

        time.sleep(0.1)

def run_sys_info():
    wlan = network.WLAN(network.STA_IF)
    
    scroll_pos = 0
    last_step_ms = time.ticks_ms()
    is_paused = True
    max_len = 10
    
    while True:
        if check_exit_hold(): return

        now = time.ticks_ms()
        
        if WIFI_SSID == "YOUR_WIFI_NAME":
            status_text = "WiFi: Not Set"
            ssid_line_text = "SSID: Set WiFi in Code"
        elif wlan.isconnected():
            status_text = "WiFi: Online"
            ssid_line_text = f"SSID: {WIFI_SSID}"
        else:
            status_text = "WiFi: Offline"
            ssid_line_text = f"SSID: {WIFI_SSID}"

        volts, pct, is_charging, batt_text = get_battery_info()

        raw_display = ssid_line_text[6:]
        if len(raw_display) > max_len:
            padded = raw_display + "   "
            double_text = padded + padded
            
            if is_paused:
                if time.ticks_diff(now, last_step_ms) > 1500:
                    is_paused = False
                    last_step_ms = now
            else:
                if time.ticks_diff(now, last_step_ms) > 250:
                    scroll_pos += 1
                    last_step_ms = now
                    
                    if scroll_pos >= len(padded):
                        scroll_pos = 0
                        is_paused = True

            ssid_display_text = double_text[scroll_pos : scroll_pos + max_len]
        else:
            ssid_display_text = raw_display

        display.fill(0)
        display.text("SYSTEM INFO", 12, 0)
        display.hline(0, 10, 128, 1)
        display.text(batt_text, 0, 15)
        display.text(status_text, 0, 28)
        display.text(f"SSID: {ssid_display_text}", 0, 40)
        display.hline(0, 52, 128, 1)
        display.text("Hold BigBtn Exit", 0, 55)
        display.show()
        
        time.sleep(0.02)

# ==============================================================================
# HOME MENU & NAVIGATION
# ==============================================================================
last_idx = -1
scroll_pos = 0
last_step_ms = time.ticks_ms()
is_paused = True

def draw_home_menu(selected_idx):
    global last_idx, scroll_pos, last_step_ms, is_paused
    
    now = time.ticks_ms()
    
    if selected_idx != last_idx:
        last_idx = selected_idx
        scroll_pos = 0
        last_step_ms = now
        is_paused = True

    display.fill(0)
    display.text("== HOME MENU ==", 4, 0)
    display.hline(0, 10, 128, 1)

    max_len = 14
    y_offsets = [15, 30, 45]

    for i, app_name in enumerate(APPS):
        y = y_offsets[i]
        
        if i == selected_idx:
            display.fill_rect(0, y - 2, 128, 12, 1)
            
            if len(app_name) > max_len:
                padded = app_name + "   "
                double_text = padded + padded
                
                if is_paused:
                    if time.ticks_diff(now, last_step_ms) > 1500:
                        is_paused = False
                        last_step_ms = now
                else:
                    if time.ticks_diff(now, last_step_ms) > 250:
                        scroll_pos += 1
                        last_step_ms = now
                        
                        if scroll_pos >= len(padded):
                            scroll_pos = 0
                            is_paused = True

                visible_text = double_text[scroll_pos : scroll_pos + max_len]
            else:
                visible_text = app_name

            display.text(f">{visible_text}", 0, y, 0)
        else:
            display.text(f" {app_name[:max_len]}", 0, y, 1)

    display.show()

# --- MAIN LOOP ---
selected_idx = 0

while True:
    draw_home_menu(selected_idx)

    if is_k1_pressed():
        time.sleep(0.05)
        if is_k1_pressed():
            selected_idx = (selected_idx + 1) % len(APPS)
            while is_k1_pressed():
                time.sleep(0.01)

    if is_pressed(btn_k2):
        time.sleep(0.05)
        if is_pressed(btn_k2):
            selected_idx = (selected_idx - 1) % len(APPS)
            while is_pressed(btn_k2):
                time.sleep(0.01)

    if is_pressed(btn_select):
        time.sleep(0.05)
        if is_pressed(btn_select):
            while is_pressed(btn_select):
                time.sleep(0.01)

            if selected_idx == 0:
                run_flight_tracker()
            elif selected_idx == 1:
                run_clock()
            elif selected_idx == 2:
                run_sys_info()

    time.sleep(0.02)
