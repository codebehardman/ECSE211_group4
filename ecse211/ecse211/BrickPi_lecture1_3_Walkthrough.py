#!/usr/bin/python3
"""DPM Sensor and Filtering (Lecture 8) - Simplelog-py

A simple program to poll the color sensor and write the results to a log file (colorSensorLog.csv).
Graceful termination when Touch sensor pressed.
Abort on ^C.

Author: F.P. Ferrie, Ryan Au 
Date: January 13th, 2022
"""

from utils.brick import BP, Motor, TouchSensor, EV3ColorSensor, wait_ready_sensors, SensorError 
import time
FORWARD_SPEED = 20              # speed constant = 30% power
SENSOR_POLL_SLEEP = 0.05        # Polling rate = 50 msec
T_SENSOR = TouchSensor(2)       # Touch Sensor in Port S2
C_SENSOR = EV3ColorSensor(1)    # Color Sensor in Port S1

try:
    f = open("colorSensor.csv", "w")            # Open a file for writing
    f.write("Data logged from color sensor.\n") # Print a header
    
    print('Waiting for sensors to initialize...')
    wait_ready_sensors()
    print("Data acquisition commencing...")     # Wait for sensors to initialize
    while True:
        try:
            if T_SENSOR.is_pressed():           # End data acquisition if sensor pressed
                print("Data acquisition complete. Closing log file.")
                f.close()                       # Close file (save contents)
                BP.reset_all()                  # Stop robot
                exit()
            
            # Retrieve the color values the Color sensor
            red, gre, blu, lum = C_SENSOR.get_value()
            
            # Write color values to the file
            f.write('{:d},{:d},{:d},{:d}\n'.format (red, gre, blu, lum))
            
            time.sleep(SENSOR_POLL_SLEEP)       # Use sensor polling interval here
        except SensorError as error:
            print(error)                        # On exception or error, print error code
except KeyboardInterrupt:
    print("Data acquisition aborted.")
    BP.reset_all()                              # Allows program to be stopped on keyboard interrupt