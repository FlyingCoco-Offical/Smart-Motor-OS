# Made by FlyingCoco-Offical as the offical launcher for SmartMotor-OS. For any issues make a Github issue.

# --- SYSTEM CONFIGURATION ---
WIFI_SSID = "YOUR_WIFI_NAME_HERE"
WIFI_PASS = "YOUR_WIFI_PASS_HERE"
OS_VERSION = "SMOS v1.0" # DO NOT EDIT

import network
import time
from machine import Pin, I2C, ADC
import ssd1306
import os

# --- HARDWARE SETUP ---
K1_PIN = 10
K2_PIN = 8
SELECT_PIN = 9
BATTERY_ADC_PIN = 0

btn_k1 = Pin(K1_PIN, Pin.IN, Pin.PULL_UP)
btn_k2 = Pin(K2_PIN, Pin.IN, Pin.PULL_UP)
btn_select = Pin(SELECT_PIN, Pin.IN, Pin.PULL_UP)

K1_ALT_PINS = [4, 5]
alt_k1_objs = [Pin(p, Pin.IN, Pin.PULL_UP) for p in K1_ALT_PINS]

batt_adc = ADC(Pin(BATTERY_ADC_PIN))
batt_adc.atten(ADC.ATTN_11DB)

i2c = I2C(0, scl=Pin(7), sda=Pin(6))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# --- HARDWARE HELPERS ---
def is_pressed(btn_pin):
    return btn_pin.value() == 0

def is_k1_pressed():
    if is_pressed(btn_k1): return True
    for alt in alt_k1_objs:
        if alt.value() == 0: return True
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
                while is_pressed(btn_select): time.sleep(0.05)
                return True
            time.sleep(0.1)
    return False

def ensure_wifi():
    if WIFI_SSID == "YOUR_WIFI_NAME": return False
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        try:
            wlan.active(False)
            time.sleep(0.3)
        except Exception: pass
        wlan.active(True)
        time.sleep(0.2)
        wlan.connect(WIFI_SSID, WIFI_PASS)
        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
    return wlan.isconnected()

def get_battery_info():
    raw_sum = sum(batt_adc.read() for _ in range(15))
    raw_avg = raw_sum / 15.0
    pin_voltage = (raw_avg / 4095.0) * 3.3
    batt_volts = pin_voltage * 6.3
    is_charging = batt_volts > 4.25

    if is_charging:
        return batt_volts, 100, True, f"BAT: CHG [CHG] ({batt_volts:.1f}V)"
    elif batt_volts < 3.0:
        return batt_volts, 0, False, f"BAT: Low ({batt_volts:.1f}V)"
    else:
        pct = max(0, min(100, int(((batt_volts - 3.2) / 1.0) * 100)))
        return batt_volts, pct, False, f"BAT: {pct}% ({batt_volts:.1f}V)"

SYS_CTX = {
    "display": display,
    "check_exit": check_exit_hold,
    "ensure_wifi": ensure_wifi,
    "get_battery": get_battery_info,
    "wifi_ssid": WIFI_SSID
}

ensure_wifi()

# --- BUILT-IN SYSTEM INFO APP ---
class BuiltinSysInfo:
    APP_NAME = "System Info"
    
    @staticmethod
    def run(sys):
        wlan = network.WLAN(network.STA_IF)
        scroll_pos = 0
        last_step_ms = time.ticks_ms()
        is_paused = True
        max_len = 16
        
        while True:
            if sys["check_exit"](): return

            now = time.ticks_ms()
            wifi_ssid = sys["wifi_ssid"]
            
            if wifi_ssid == "YOUR_WIFI_NAME":
                wifi_line = "WiFi: Off | Not Set"
            elif wlan.isconnected():
                wifi_line = f"WiFi: On | {wifi_ssid}"
            else:
                wifi_line = f"WiFi: Off | {wifi_ssid}"

            volts, pct, is_charging, batt_text = sys["get_battery"]()

            if len(wifi_line) > max_len:
                padded = wifi_line + "   "
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

                wifi_display_text = double_text[scroll_pos : scroll_pos + max_len]
            else:
                wifi_display_text = wifi_line

            sys["display"].fill(0)
            sys["display"].text("SYSTEM INFO", 12, 0)
            sys["display"].hline(0, 10, 128, 1)
            sys["display"].text(f"OS: {OS_VERSION}", 0, 15)
            sys["display"].text(batt_text, 0, 28)
            sys["display"].text(wifi_display_text, 0, 40)
            sys["display"].hline(0, 52, 128, 1)
            sys["display"].text("Hold BigBtn Exit", 0, 55)
            sys["display"].show()
            
            time.sleep(0.02)

# --- DYNAMICALLY DISCOVER & LOAD EXTERNAL APPS ---
external_apps = []

try:
    file_list = os.listdir()
except Exception:
    file_list = []

for filename in file_list:
    if filename.startswith("app_") and filename.endswith(".py"):
        mod_name = filename[:-3]
        try:
            mod = __import__(mod_name)
            if getattr(mod, "ENABLE_APP", False):
                external_apps.append(mod)
        except Exception as e:
            print(f"Failed to load {mod_name}: {e}")

# Sort external apps by order preference or name
external_apps.sort(key=lambda x: (getattr(x, "APP_ORDER", 999), getattr(x, "APP_NAME", "")))

# Always append System Info as the final entry in active_apps
active_apps = external_apps + [BuiltinSysInfo]

# --- HOME MENU LOOP ---
selected_idx = 0
last_idx = -1
scroll_pos = 0
last_step_ms = time.ticks_ms()
is_paused = True

def draw_menu(selected_idx):
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
    start_i = max(0, min(selected_idx, len(active_apps) - 3))
    visible = active_apps[start_i : start_i + 3]

    for i, mod in enumerate(visible):
        app_i = start_i + i
        y = 15 + (i * 15)
        name = getattr(mod, "APP_NAME", "App")

        if app_i == selected_idx:
            display.fill_rect(0, y - 2, 128, 12, 1)
            if len(name) > max_len:
                padded = name + "   "
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
                vis_name = double_text[scroll_pos : scroll_pos + max_len]
            else:
                vis_name = name
            display.text(f">{vis_name}", 0, y, 0)
        else:
            display.text(f" {name[:max_len]}", 0, y, 1)

    display.show()

while True:
    draw_menu(selected_idx)

    if is_k1_pressed():
        time.sleep(0.05)
        if is_k1_pressed():
            selected_idx = (selected_idx + 1) % len(active_apps)
            while is_k1_pressed(): time.sleep(0.01)

    if is_pressed(btn_k2):
        time.sleep(0.05)
        if is_pressed(btn_k2):
            selected_idx = (selected_idx - 1) % len(active_apps)
            while is_pressed(btn_k2): time.sleep(0.01)

    if is_pressed(btn_select):
        time.sleep(0.05)
        if is_pressed(btn_select):
            while is_pressed(btn_select): time.sleep(0.01)
            active_apps[selected_idx].run(SYS_CTX)

    time.sleep(0.02)

