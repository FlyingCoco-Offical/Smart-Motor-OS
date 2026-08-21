# Made by FlyingCoco-Offical as an offical app for SmartMotor-OS. For any issues make a Github issue.

# --- APP CONFIGURATION ---
ENABLE_APP = True
APP_ORDER = 2  # 1 shows first, 2 shows second, etc.

USE_24HR_TIME = False
EUROPEAN_DATE_FORMAT = False

import time
import urequests
import ntptime

APP_NAME = "Digital Clock"
IP_GEO_URL = "http://ip-api.com/json/?fields=timezone,offset"

def get_auto_timezone():
    tz_name = "LOCAL"
    offset_secs = -28800
    try:
        res = urequests.get(IP_GEO_URL, timeout=5)
        if res.status_code == 200:
            data = res.json()
            res.close()
            tz_name = data.get("timezone", "LOCAL").split("/")[-1]
            offset_secs = data.get("offset", -28800)
    except Exception:
        pass
    return tz_name, offset_secs

def run(sys):
    tz_name = "LOCAL"
    offset_secs = -28800

    if sys["ensure_wifi"]():
        try:
            ntptime.settime()
        except Exception:
            pass
        tz_name, offset_secs = get_auto_timezone()

    while True:
        if sys["check_exit"](): return

        utc_secs = time.time()
        local_secs = utc_secs + offset_secs
        tm = time.localtime(local_secs)
        
        year, month, mday, hour, minute, second, _, _ = tm
        
        if USE_24HR_TIME:
            time_str = f"{hour:02d}:{minute:02d}:{second:02d}"
        else:
            ampm = "AM" if hour < 12 else "PM"
            disp_hour = hour % 12
            if disp_hour == 0: disp_hour = 12
            time_str = f"{disp_hour:02d}:{minute:02d}:{second:02d} {ampm}"
            
        if EUROPEAN_DATE_FORMAT:
            date_str = f"{mday:02d}/{month:02d}/{year}"
        else:
            date_str = f"{month:02d}/{mday:02d}/{year}"

        sys["display"].fill(0)
        sys["display"].text(f"TZ: {tz_name[:12]}", 0, 0)
        sys["display"].hline(0, 10, 128, 1)
        sys["display"].text(time_str, 8 if USE_24HR_TIME else 16, 22)
        sys["display"].text(date_str, 24, 36)
        sys["display"].hline(0, 50, 128, 1)
        sys["display"].text("Hold BigBtn Exit", 0, 54)
        sys["display"].show()

        time.sleep(0.1)
