#!/usr/bin/env python3

"""
Module to play sounds when the touch sensor is pressed.
This file must be run on the robot.
"""
 
from utils import sound
from utils.brick import TouchSensor, configure_ports

SOUND = sound.Sound(duration=0.3, pitch="A4", volume=60)
TOUCH_SENSOR = configure_ports(PORT_1=TouchSensor)


def play_sound():
    "Play a single note."
    SOUND.play()
    SOUND.wait_done()


def play_sound_on_button_press():
    "In an infinite loop, play a single note when the touch sensor is pressed."
    try:
        while True:
            touch_data = TOUCH_SENSOR.get_value()
            print(touch_data)
            if touch_data:
                play_sound()
    except BaseException:  # capture all exceptions including KeyboardInterrupt (Ctrl-C)
        exit()


if __name__=='__main__':
    play_sound()

    # TODO Implement this function
    play_sound_on_button_press()
