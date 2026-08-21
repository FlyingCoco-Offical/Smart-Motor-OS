# Made by FlyingCoco-Offical as an offical app for SmartMotor-OS. For any issues make a Github issue.

# --- APP CONFIGURATION ---
ENABLE_APP = True
APP_ORDER = 2

K_NEIGHBORS = 3 

APP_NAME = "Servo K-NN"

import time
import math
import machine
from machine import Pin, ADC, I2C
import ssd1306
import adxl345
import files
import prefs

# Hardware Pin Assignments
POT_PIN = 26        # ADC0
LIGHT_PIN = 27      # ADC1
SERVO_PIN = 15      # PWM
I2C_SDA_PIN = 0     # OLED & ADXL345 SDA
I2C_SCL_PIN = 1     # OLED & ADXL345 SCL


class App:
    def __init__(self, display, i2c):
        self.display = display
        self.i2c = i2c
        
        # Machine / Hardware Setup
        self.pot = ADC(Pin(POT_PIN))
        self.light = ADC(Pin(LIGHT_PIN))
        self.accel = adxl345.ADXL345(self.i2c)
        
        self.servo = machine.PWM(Pin(SERVO_PIN))
        self.servo.freq(50)
        
        # k-NN configuration setting stored directly in class
        self.k = K_NEIGHBORS
        
        # Load classification dataset
        self.dataset = files.load_dataset()

    def set_servo_angle(self, angle):
        """Sets servo angle between 0 and 180 degrees."""
        angle = max(0, min(180, angle))
        duty = int(1638 + (angle / 180.0) * 6554)
        self.servo.duty_u16(duty)

    def read_sensors(self):
        """Reads and normalizes all sensor inputs."""
        p_val = self.pot.read_u16() / 65535.0
        l_val = self.light.read_u16() / 65535.0
        ax, ay, az = self.accel.get_axes_scaled()
        return [p_val, l_val, ax, ay, az]

    def classify_knn(self, new_point):
        """Classifies sensor input using stored dataset and internal k parameter."""
        if not self.dataset:
            return "No Data"
            
        distances = []
        for item in self.dataset:
            features = item['features']
            label = item['label']
            dist = math.sqrt(sum((f - n) ** 2 for f, n in zip(features, new_point)))
            distances.append((dist, label))
            
        distances.sort(key=lambda x: x[0])
        effective_k = min(self.k, len(distances))
        k_neighbors = distances[:effective_k]
        
        votes = {}
        for _, label in k_neighbors:
            votes[label] = votes.get(label, 0) + 1
            
        return max(votes, key=votes.get)

    def actuate(self, label):
        """Actuates servo position depending on predicted label."""
        if label == "POS_A" or label == 0:
            self.set_servo_angle(30)
        elif label == "POS_B" or label == 1:
            self.set_servo_angle(90)
        elif label == "POS_C" or label == 2:
            self.set_servo_angle(150)

    def draw(self, label):
        """Renders status output on the screen."""
        self.display.fill(0)
        self.display.text(f"App: {APP_NAME}", 0, 0)
        self.display.text(f"k-NN (k={self.k})", 0, 16)
        self.display.text(f"Class: {label}", 0, 32)
        self.display.show()

    def run(self):
        """Main execution loop called by the launcher."""
        running = True
        while running:
            sensor_data = self.read_sensors()
            label = self.classify_knn(sensor_data)
            
            self.actuate(label)
            self.draw(label)
            
            time.sleep(0.05)


# Standard launcher execution entry point
def main(display, i2c):
    if APP_ENABLED:
        app = App(display, i2c)
        app.run()

