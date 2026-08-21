# Made by (INPUT_GITHUB_USERNAME) as an unoffical app for SmartMotor-OS. For any issues make a Github issue and mention the app creator.

# ==============================================================================
# APP CONFIGURATION
# ==============================================================================
ENABLE_APP = False
APP_ORDER = 9  # 1 shows first, 2 shows second, etc.

# Add custom app settings here
CUSTOM_SETTING = "Hello World"

import time

APP_NAME = "My Custom App"  # Name shown on Home Menu

def run(sys):
    """
    Main app loop.
    Use sys['display'] to draw on screen.
    Use sys['check_exit']() to check if user held exit button.
    """
    while True:
        # ALWAYS check exit at the top of your loop
        if sys["check_exit"]():
            return

        # --- DRAW DISPLAY ---
        sys["display"].fill(0)
        sys["display"].text(APP_NAME[:15], 0, 0)
        sys["display"].hline(0, 10, 128, 1)
        
        sys["display"].text(CUSTOM_SETTING, 0, 25)
        
        sys["display"].hline(0, 50, 128, 1)
        sys["display"].text("Hold BigBtn Exit", 0, 54)
        sys["display"].show()

        time.sleep(0.1)
