# Smart-Motor-OS
Using [Smart Motors V3](https://smartmotors.ai/) made at Tufts Center for Engineering Education and Outreach.

### Navigation
The Smart Motor V3 is equipped with one main select button, two side K1/K2 buttons, as well as a potentiometer. To scroll in the main interface, use the top K button to move up, and the bottom K button to move down. Press the main select button to enter an app. If you want to leave an app, hold the select button for five (5) seconds.

### Current Apps
As someone who aspires to be a pilot in the future, the first app had to be a Flight Tracker. Using OpenSky's free API, Smart Motor OS is able to track any nearby planes using an airport code (e.g., KLAX) or coordinates for more custom uses.
(add image here)


Secondly, we have a Clock that uses the devices IP to determine its current timezone and adjust accordingly. It has support for 12 and 24 hour clock as well as MM/DD/YYYY and DD/MM/YYYY date formats.
(add image here)


Finally, there is the Device Info app which gives Battery data and WiFi status.
(add image here)

### Future Plans
I have plans on making the code more "modular". Instead of having them all on main.py, I want to move to having flighttracker.py, clock.py and device-info.py and depending on which you upload to your device, it will run those apps automatically.
