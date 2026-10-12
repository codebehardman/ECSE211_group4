#!/usr/bin/env python3
"""
ECSE 211 - Lab 1: Wall Following

The wall is on the RIGHT side of the robot.
The ultrasonic sensor is mounted at the front-right, pointing diagonally
forward-right (about 45 degrees), so it sees both the side wall and any wall
coming up ahead (concave corners).

Choose the controller by changing MODE below, then deploy and run.
Stop with Ctrl+C or the "Reset Robot" button in deploy_to_robot.py.
"""

import atexit
import math
import signal
import sys
import threading
import time
from utils.brick import Motor, EV3UltrasonicSensor, TouchSensor, wait_ready_sensors, reset_brick


# ============================ SETTINGS ============================

MODE = "bangbang"        # "bangbang" or "p"

# --- Hardware ---
LEFT_MOTOR_PORT = "A"    # outer wheel (far from the wall)
RIGHT_MOTOR_PORT = "D"   # inner wheel (close to the wall)
US_SENSOR_PORT = 1       # sensor port number (S1-S4) -- CHECK THIS, see notes
MOTOR_DIRECTION = -1     # -1 because our motors are mounted backwards (1 drove in reverse)
TOUCH_PORT = None        # set to a sensor port number (e.g. 2) if you add a touch sensor as a stop button
MAX_RUN_TIME = 120       # seconds, robot stops by itself after this (None = run forever)
SENSOR_ANGLE_DEG = 45    # angle between the sensor and the robot's forward direction

# --- Controller ---
BAND_CENTER = 20
P_BAND_CENTER = 45# cm, target distance from the wall (lab requirement)
BAND_WIDTH = 3           # cm, bang-bang "do nothing" zone (lab requirement)
BASE_SPEED = 180         # deg/s, speed of both wheels when on track
BB_DELTA = 90            # deg/s, bang-bang: how much the outer wheel speeds up / slows down
KP = 8                   # deg/s per cm of error, p-controller gain
MAX_CORRECTION = 150     # deg/s, cap on the p-controller correction
TOO_CLOSE = 10           # cm, emergency: closer than this -> spin away from the wall
SPIN_SPEED = 120         # deg/s, wheel speed used for the emergency spin

# --- Sensor filter (handles gaps and bad readings) ---
MAX_VALID = 150          # cm, anything larger is capped ("no wall seen")
JUMP = 15                # cm, a sudden increase bigger than this is suspicious
FILTER_COUNT = 5       # suspicious readings in a row before we believe them

LOOP_DELAY = 0.05        # seconds between sensor readings

# ==================================================================


left_motor = Motor(LEFT_MOTOR_PORT)
right_motor = Motor(RIGHT_MOTOR_PORT)
us_sensor = EV3UltrasonicSensor(US_SENSOR_PORT)
touch_sensor = TouchSensor(TOUCH_PORT) if TOUCH_PORT else None


def stop_robot(*_):
    """Stop the motors and exit. Runs on Ctrl+C, Thonny's Stop button, or normal exit."""
    reset_brick()
    print("Robot stopped.")
    sys.exit(0)


# Make sure the motors stop however the program ends
atexit.register(reset_brick)
signal.signal(signal.SIGINT, stop_robot)    # Ctrl+C / Thonny Stop
signal.signal(signal.SIGTERM, stop_robot)   # process killed

stop_requested = threading.Event()


def wait_for_enter():
    """Runs in the background: pressing Enter in the Shell asks the robot to stop."""
    input("Press Enter in the Shell to stop the robot.\n")
    stop_requested.set()


last_good_distance = BAND_CENTER
suspicious_count = 0


def to_wall_distance(raw_cm):
    """Convert the diagonal sensor reading into the sideways distance to the wall."""
    return raw_cm * math.sin(math.radians(SENSOR_ANGLE_DEG))


def filtered_distance(raw_cm):
    """
    Return a cleaned-up distance to the wall.
    - None (sensor error): reuse the last good value.
    - Sudden big jump away (gap or glitch): ignore it unless it keeps happening
      FILTER_COUNT times in a row (then it's a real convex corner).
    """
    global last_good_distance, suspicious_count

    if raw_cm is None:
        raw_cm = MAX_VALID

    distance = to_wall_distance(min(raw_cm, MAX_VALID))

    if distance - last_good_distance > JUMP:
        suspicious_count += 1
        if suspicious_count < FILTER_COUNT:
            return last_good_distance  # probably a gap or a glitch, ignore
    suspicious_count = 0
    last_good_distance = distance
    return distance


def bang_bang(error):
    """Outer (left) wheel changes speed, inner (right) wheel stays constant."""
    if abs(error) <= BAND_WIDTH:
        return BASE_SPEED, BASE_SPEED              # in the band: go straight
    if error > 0:
        return BASE_SPEED + BB_DELTA, BASE_SPEED   # too far: turn right, toward the wall
    return BASE_SPEED - BB_DELTA, BASE_SPEED       # too close: turn left, away from the wall


def p_control(error):
    """Correction proportional to the error, split across both wheels."""
    correction = KP * error
    correction = max(-MAX_CORRECTION, min(MAX_CORRECTION, correction))
    return BASE_SPEED + correction, BASE_SPEED - correction


def set_speeds(left, right):
    left_motor.set_dps(MOTOR_DIRECTION * left)
    right_motor.set_dps(MOTOR_DIRECTION * right)


def main():
    wait_ready_sensors()
    print(f"Sensors ready. Running {MODE} controller.")

    controller = bang_bang if MODE == "bangbang" else p_control
    threading.Thread(target=wait_for_enter, daemon=True).start()
    start = time.time()

    try:
        with open(f"log_{MODE}.csv", "w") as log:
            log.write("time,raw_cm,distance_cm,left_dps,right_dps\n")

            while True:
                if stop_requested.is_set():
                    print("Stop requested.")
                    break
                if MAX_RUN_TIME and time.time() - start > MAX_RUN_TIME:
                    print("Time limit reached.")
                    break
                if touch_sensor and touch_sensor.is_pressed():
                    print("Touch sensor pressed.")
                    break

                raw = us_sensor.get_cm()
                distance = filtered_distance(raw)
                error = distance - (P_BAND_CENTER if MODE == "p" else BAND_CENTER)

                if distance < TOO_CLOSE:
                    left, right = -SPIN_SPEED, SPIN_SPEED   # spin left, away from the wall
                else:
                    left, right = controller(error)

                set_speeds(left, right)
                log.write("%.2f,%s,%.1f,%.0f,%.0f\n" % (time.time() - start, raw, distance, left, right))
                time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        reset_brick()  # always stop the motors
        print("Robot stopped.")


if __name__ == "__main__":
    main()
