#!/usr/bin/env python3

"""
This test is used to collect data from the color sensor.
It must be run on the robot.
"""

from utils.brick import EV3ColorSensor, TouchSensor, configure_ports


COLOR_SENSOR_DATA_FILE = "../data_analysis/color_sensor.csv"

TOUCH_SENSOR, COLOR_SENSOR = configure_ports(PORT_1=TouchSensor, PORT_3=EV3ColorSensor)


def collect_color_sensor_data():
    "Collect color sensor data."
    output_file = None
    try:
        output_file = open(COLOR_SENSOR_DATA_FILE, "w")
        while True:
            color_data = COLOR_SENSOR.get_value()
            if TOUCH_SENSOR.is_pressed() and color_data is not None:
                print(color_data[:-1])
                output_file.write(f"{color_data[0]},{color_data[1]},{color_data[2]}\n")  # r,g,b format
    except BaseException as e:  # capture all exceptions including KeyboardInterrupt (Ctrl-C)
        print(e)
    finally:
        print("Done Collecting Color Sensor data")
        output_file.close()
        exit()


if __name__ == "__main__":
    collect_color_sensor_data()
