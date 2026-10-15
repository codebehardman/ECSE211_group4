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

import math
import time
from utils.brick import Motor, EV3UltrasonicSensor, wait_ready_sensors, reset_brick


# ============================ SETTINGS ============================

MODE = "bangbang"        # "bangbang" or "p"

# --- Hardware ---
LEFT_MOTOR_PORT = "A"    # outer wheel (far from the wall)
RIGHT_MOTOR_PORT = "D"   # inner wheel (close to the wall)
US_SENSOR_PORT = 1       # sensor port number (S1-S4) -- CHECK THIS, see notes
MOTOR_DIRECTION = 1      # change to -1 if the robot drives backwards
SENSOR_ANGLE_DEG = 45    # angle between the sensor and the robot's forward direction

# --- Controller ---
BAND_CENTER = 20         # cm, target distance from the wall (lab requirement)
BAND_WIDTH = 3           # cm, bang-bang "do nothing" zone (lab requirement)
BASE_SPEED = 180         # deg/s, speed of both wheels when on track
BB_DELTA = 90            # deg/s, bang-bang: how much the outer wheel speeds up / slows down
KP = 8                   # deg/s per cm of error, p-controller gain
MAX_CORRECTION = 120     # deg/s, cap on the p-controller correction
TOO_CLOSE = 10           # cm, emergency: closer than this -> spin away from the wall
SPIN_SPEED = 120         # deg/s, wheel speed used for the emergency spin

# --- Sensor filter (handles gaps and bad readings) ---
MAX_VALID = 150          # cm, anything larger is capped ("no wall seen")
JUMP = 15                # cm, a sudden increase bigger than this is suspicious
FILTER_COUNT = 5         # suspicious readings in a row before we believe them

LOOP_DELAY = 0.05        # seconds between sensor readings

# ==================================================================


left_motor = Motor(LEFT_MOTOR_PORT)
right_motor = Motor(RIGHT_MOTOR_PORT)
us_sensor = EV3UltrasonicSensor(US_SENSOR_PORT)

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
        return last_good_distance

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
    start = time.time()

    try:
        with open(f"log_{MODE}.csv", "w") as log:
            log.write("time,raw_cm,distance_cm,left_dps,right_dps\n")

            while True:
                raw = us_sensor.get_cm()
                distance = filtered_distance(raw)
                error = distance - BAND_CENTER

                if distance < TOO_CLOSE:
                    left, right = -SPIN_SPEED, SPIN_SPEED   # spin left, away from the wall
                else:
                    left, right = controller(error)

                set_speeds(left, right)
                log.write(f"{time.time() - start:.2f},{raw},{distance:.1f},{left:.0f},{right:.0f}\n")
                time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        reset_brick()  # always stop the motors


if __name__ == "__main__":
    main()