# Made by FlyingCoco-Offical as an offical app for SmartMotor-OS. For any issues make a Github issue.

# --- APP CONFIGURATION ---
ENABLE_APP = True
APP_ORDER = 3

import time
import network

# --- SYSTEM METADATA ---
OS_VERSION = "SMOS v1.0"

APP_NAME = "System Info"

def run(sys):
    wlan = network.WLAN(network.STA_IF)
    scroll_pos = 0
    last_step_ms = time.ticks_ms()
    is_paused = True
    max_len = 16  # Adjusted width for full screen layout
    
    while True:
        if sys["check_exit"](): return

        now = time.ticks_ms()
        wifi_ssid = sys["wifi_ssid"]
        
        # Determine online state and combine status with SSID
        if wifi_ssid == "YOUR_WIFI_NAME":
            wifi_line = "WiFi: Off | Not Set"
        elif wlan.isconnected():
            wifi_line = f"WiFi: On | {wifi_ssid}"
        else:
            wifi_line = f"WiFi: Off | {wifi_ssid}"

        volts, pct, is_charging, batt_text = sys["get_battery"]()

        # Handle horizontal auto-scrolling for long Wi-Fi strings
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
        
        # Display OS Version in place of the removed SSID line
        sys["display"].text(f"OS: {OS_VERSION}", 0, 15)
        sys["display"].text(batt_text, 0, 28)
        sys["display"].text(wifi_display_text, 0, 40)
        
        sys["display"].hline(0, 52, 128, 1)
        sys["display"].text("[Hold BigBtn Exit]", 0, 55)
        sys["display"].show()
        
        time.sleep(0.02)
