#!/usr/bin/env python3

"""
This test is used to collect data from the color sensor.
It must be run on the robot.
"""

# Add your imports here, if any
from utils.brick import EV3ColorSensor, configure_ports


COLOR_SENSOR_DATA_FILE = "../data_analysis/color_sensor.csv"

# complete this based on your hardware setup
..., ... = configure_ports(...)


def collect_color_sensor_data():
    "Collect color sensor data."
    ...


if __name__ == "__main__":
    collect_color_sensor_data()
