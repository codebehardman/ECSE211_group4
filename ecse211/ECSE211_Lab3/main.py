from threading import Thread
from utils.sound import Sound
from utils.brick import TouchSensor, EV3UltrasonicSensor, Motor
from time import sleep

NOTE_C = Sound(duration=0.5, volume=80, pitch="C5")
NOTE_D = Sound(duration=0.5, volume=80, pitch="D5")
NOTE_F = Sound(duration=0.5, volume=80, pitch="F5")
NOTE_G = Sound(duration=0.5, volume=80, pitch="G5")

TOUCH_SENSOR_1 = TouchSensor(1)
TOUCH_SENSOR_2 = TouchSensor(2)
US_SENSOR = EV3UltrasonicSensor(3)
MOTOR = Motor("A")
MOTOR.reset_encoder()

# motor constants
ANGLE = 90
PERIOD = 1

# state
drums_is_active = False
running = True


def play_sound(note):
    note.play()
    note.wait_done()

def play_flute():
    global running, drums_is_active
    try:
        while running:
            us_sensor_is_activated = False
            us_sensor_distance = US_SENSOR.get_value()
            if us_sensor_distance:
                us_sensor_is_activated = us_sensor_distance < 5

            # emergency stop
            if (TOUCH_SENSOR_1.is_pressed() and TOUCH_SENSOR_2.is_pressed()
                and us_sensor_is_activated):
                print("Emergency stop activated")
                running = False
            
            # drums
            if (TOUCH_SENSOR_1.is_pressed() and TOUCH_SENSOR_2.is_pressed()
                and not us_sensor_is_activated):
                if (drums_is_active):
                    print("Drums deactivated")
                    drums_is_active = False
                else:
                    print("Drums activated")
                    drums_is_active = True

            # notes in ultrasonic deactivated mode
            if not us_sensor_is_activated:
                if TOUCH_SENSOR_1.is_pressed():
                    play_sound(NOTE_C)
                elif TOUCH_SENSOR_2.is_pressed():
                    play_sound(NOTE_D)
            
            # notes in ultrasonic activated mode
            elif us_sensor_is_activated:
                if TOUCH_SENSOR_1.is_pressed():
                    play_sound(NOTE_F)
                elif TOUCH_SENSOR_2.is_pressed():
                    play_sound(NOTE_G)

            sleep(0.05)          
    except BaseException as e:
        print("Flute thread error:", e)
        running = False

def play_drums():
    global running, drums_is_active
    try:
        while running:
            if drums_is_active:
                MOTOR.set_position_relative(-ANGLE)
                sleep(0.5)
                MOTOR.set_position_relative(ANGLE)
                sleep(0.5)
            sleep(0.05)
    except BaseException as e:
        print("Drum thread error:", e)
        running = False

def main():
    flute_thread = Thread(target=play_flute)
    drum_thread = Thread(target=play_drums)
    flute_thread.start()
    drum_thread.start()

    flute_thread.join()
    drum_thread.join()

if __name__=='__main__':
    main()
