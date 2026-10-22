#!/usr/bin/env python3
"""
ECSE 211 - Lab 2: Odometry

Conventions (Figure 1 of the handout):
  - theta is a compass-style heading: 0 = facing +y, measured CLOCKWISE.
  - Left wheel forward + right wheel backward  -> theta increases.
  - x = d * sin(theta), y = d * cos(theta).
  - (0, 0) is the grid intersection one tile up/right of the board's bottom-left
    corner (Figure 2). S (centre of the bottom-left tile) is (-15.24, -15.24).

Modes:
  "square" -> drive the 3x3-tile square from S with light-sensor correction
  "float"  -> float the motors so the TA can push the robot by hand
  "straight" -> tuning: drive 2 tiles forward, then compare printed y with a tape measure
  "turn"   -> tuning: make four 90 deg turns (one full turn) to check TRACK
  "sensors" -> tuning: motors float, prints both light readings so you can slide
              the robot over a line by hand and check the thresholds
  "raw"    -> tuning: motors float, prints ONLY the raw readings of both sensors
              (no calibration, no thresholds) so each sensor can be calibrated

Stop with Ctrl+C.
"""

import atexit
import math
import signal
import sys
import threading
import time
from utils.brick import Motor, EV3ColorSensor, NXTColorSensor, reset_brick


# ============================ SETTINGS ============================

MODE = "square"          # "square", "float", "straight", "turn", "sensors" or "raw"

# --- Hardware (same motor setup as Lab 1) ---
LEFT_MOTOR_PORT = "D"
RIGHT_MOTOR_PORT = "A"
LEFT_LIGHT_PORT = 2      # port of the sensor mounted on the robot's LEFT side (NXT)
RIGHT_LIGHT_PORT = 4     # port of the sensor mounted on the robot's RIGHT side (EV3)
LEFT_LIGHT_TYPE = "NXT"  # CHECK: "EV3" or "NXT" (printed on the sensor)
RIGHT_LIGHT_TYPE = "EV3" # CHECK: "EV3" or "NXT"
MOTOR_DIRECTION = 1      # motors flipped around after Lab 2 (was -1)

# --- Robot geometry (MEASURE, then tune) ---
WHEEL_RADIUS = 2.10      # cm
RIGHT_WHEEL_SCALE = 1.0  # right wheel's effective size / left wheel's. >1 if it curves LEFT while theta reads 0
TRACK = 11.3            # cm, distance between the two wheels' contact points
SENSOR_OFFSET = 5    # cm, how far AHEAD of the wheel axle the light sensors sit
SENSOR_SPACING = 10.0    # cm, measured: distance between the two light sensors (left to right)

# --- Board ---
TILE = 30.48             # cm
START_X = -TILE / 2      # S = centre of the bottom-left tile
START_Y = -TILE / 2
START_THETA = 0.0        # facing +y

# --- Motion ---
FORWARD_SPEED = 150      # deg/s
SLOW_SPEED = 95          # deg/s, speed near a line: both sensors must reach it at the SAME speed
# or the faster one overshoots more and the robot lines up crooked
TURN_SPEED = 60        # deg/s
TURN_SLOW_SPEED = 40     # deg/s, last few degrees of a turn
TURN_TOLERANCE = 1.0     # deg, a turn is done when within this of the target
KP_HEADING = 4.0         # deg/s of wheel speed difference per degree of heading error
MAX_HEADING_CORR = 50    # deg/s, cap on the heading correction
MAX_ALIGN_TURN = 15    # deg, if lining up on a line rotates us more than this, it was the wrong line
LINE_CLEAR = 4.0         # cm to drive after a line so it isn't detected twice
MAX_LINE_WAIT = 2.0      # s, give up waiting for the second sensor after this
LINE_WINDOW = 5.0        # cm, slow down and look for a line once the sensors are this close to it
ALIGN_TRIM = 0        # deg, how crooked the robot really is after lining up (see "rotated" prints).
# Set to the average "rotated" value from a square run if it is always the same sign.
MAX_HIT_GAP = 4.0        # cm, if the 2nd sensor hasn't crossed this far after the 1st, give up on it
MAX_POS_FIX = 4.0        # cm, a line that would move the odometer more than this is treated as a false reading
MAX_ANGLE_FIX = 6.0      # deg, a measured angle bigger than this is treated as noise
ANGLE_GAIN = 0.0         # fraction of the measured angle error applied at each line (0-1)
LINE_SLACK = 6.0         # cm, if no line is seen this far past where it should be, it was missed

# --- Light sensor ---
# A sensor sees a line when its reading drops below RATIO x (its own wood reading).
# Each sensor gets its own ratio: use MODE = "sensors" to see what % of wood each one reads on a line,
# then pick a ratio about halfway between that % and 100%.
LEFT_LINE_RATIO = 0.97   # measured: wood sum ~1370 (1350-1388), line ~1296 (1286-1305) -> threshold ~1329
RIGHT_LINE_RATIO = 0.75  # measured: wood red ~22 (18-23), line ~13.5 (13-14) -> threshold ~16.5
LINE_CONFIRM_DIST = 0.3  # cm a sensor must stay dark before a line counts (filters noise)

# --- Odometer ---
ODO_PERIOD = 0.01        # s between odometer updates
PRINT_PERIOD = 0.25      # s between console prints

# ==================================================================


left_motor = Motor(LEFT_MOTOR_PORT)
right_motor = Motor(RIGHT_MOTOR_PORT)


def make_light_sensor(port, kind):
    if kind.upper() == "NXT":
        return NXTColorSensor(port)               # NXT only supports component (RGB) mode
    return EV3ColorSensor(port, mode="red")


# Light sensors are only created in square mode, so float mode works without them
USES_LIGHT = MODE in ("square", "sensors", "raw")
left_light = make_light_sensor(LEFT_LIGHT_PORT, LEFT_LIGHT_TYPE) if USES_LIGHT else None
right_light = make_light_sensor(RIGHT_LIGHT_PORT, RIGHT_LIGHT_TYPE) if USES_LIGHT else None


def stop_robot(*_):
    reset_brick()
    print("Robot stopped.")
    sys.exit(0)


atexit.register(reset_brick)
signal.signal(signal.SIGINT, stop_robot)
signal.signal(signal.SIGTERM, stop_robot)


# ============================ ODOMETER ============================

odo_lock = threading.Lock()
x, y, theta = 0.0, 0.0, 0.0
last_left, last_right = 0, 0
last_print = 0.0


def read_encoders():
    """Encoder positions in degrees, positive = that wheel rolled forward."""
    return (MOTOR_DIRECTION * left_motor.get_encoder(),
            MOTOR_DIRECTION * right_motor.get_encoder())


def wrap_angle(angle):
    """Keep theta in [0, 360)."""
    angle %= 360
    return 0.0 if angle >= 360 else angle


def init_odometer(x0, y0, theta0):
    global x, y, theta, last_left, last_right
    with odo_lock:
        last_left, last_right = read_encoders()
        x, y, theta = x0, y0, wrap_angle(theta0)


def get_odometer():
    with odo_lock:
        return x, y, theta


def set_odometer(new_x=None, new_y=None, new_theta=None):
    """Overwrite parts of the pose (used by the light correction)."""
    global x, y, theta
    with odo_lock:
        if new_x is not None:
            x = new_x
        if new_y is not None:
            y = new_y
        if new_theta is not None:
            theta = wrap_angle(new_theta)


def print_pose(prefix=""):
    shown_theta = round(theta, 1) % 360   # never display 360.0
    print(f"{prefix}x = {x:7.2f} cm   y = {y:7.2f} cm   theta = {shown_theta:5.1f} deg")


def update_odometer():
    """Update (x, y, theta) from the change in encoder readings since the last call."""
    global x, y, theta, last_left, last_right, last_print
    with odo_lock:
        enc_left, enc_right = read_encoders()
        d_left = math.radians(enc_left - last_left) * WHEEL_RADIUS     # cm
        d_right = math.radians(enc_right - last_right) * WHEEL_RADIUS * RIGHT_WHEEL_SCALE  # cm
        last_left, last_right = enc_left, enc_right

        d = (d_left + d_right) / 2                                # distance of the centre
        d_theta = math.degrees((d_left - d_right) / TRACK)        # clockwise positive

        heading = math.radians(theta + d_theta / 2)               # mid-step heading
        x += d * math.sin(heading)
        y += d * math.cos(heading)
        theta = wrap_angle(theta + d_theta)

        now = time.time()
        if now - last_print >= PRINT_PERIOD:
            last_print = now
            print_pose()


odo_running = threading.Event()


def odometer_loop():
    while odo_running.is_set():
        update_odometer()
        time.sleep(ODO_PERIOD)


# Required by the handout, as-is.
def float_motors():
    left_motor.float_motor()
    right_motor.float_motor()

    while(True):
        update_odometer()
        time.sleep(0.01)


# ============================ MOTION ============================

def set_speeds(left, right):
    left_motor.set_dps(MOTOR_DIRECTION * left)
    right_motor.set_dps(MOTOR_DIRECTION * right)


def stop():
    set_speeds(0, 0)
    time.sleep(0.1)


def heading_error(target):
    """Signed degrees to turn to reach target, in [-180, 180). Positive = turn clockwise."""
    _, _, t = get_odometer()
    return (target - t + 540) % 360 - 180


def hold_heading(heading, speed):
    """Wheel speeds that drive forward while steering back onto heading (P control)."""
    correction = KP_HEADING * heading_error(heading)
    correction = max(-MAX_HEADING_CORR, min(MAX_HEADING_CORR, correction))
    return speed + correction, speed - correction   # left faster -> turns clockwise


def drive_distance(dist, heading):
    """Drive straight forward along heading for dist cm, measured by the odometer."""
    x0, y0, _ = get_odometer()
    while True:
        cx, cy, _ = get_odometer()
        if math.hypot(cx - x0, cy - y0) >= dist:
            break
        set_speeds(*hold_heading(heading, FORWARD_SPEED))
        time.sleep(0.005)
    stop()


def drive_until(axis, target, sign, heading):
    """Drive forward along heading until the axle's x or y coordinate reaches target."""
    while True:
        cx, cy, _ = get_odometer()
        pos = cy if axis == "y" else cx
        if (pos - target) * sign >= 0:
            break
        set_speeds(*hold_heading(heading, FORWARD_SPEED))
        time.sleep(0.005)
    stop()


def turn_to(target):
    """Turn in place (whichever way is shorter) until theta is within TURN_TOLERANCE of target."""
    while True:
        error = heading_error(target)
        if abs(error) <= TURN_TOLERANCE:
            break
        speed = TURN_SLOW_SPEED if abs(error) < 15 else TURN_SPEED
        if error < 0:
            speed = -speed                       # overshot: turn back counter-clockwise
        set_speeds(speed, -speed)                # left fwd, right back -> theta up
        time.sleep(0.005)
    stop()


# ============================ LIGHT CORRECTION ============================

left_wood = right_wood = 0.0
left_threshold = right_threshold = 0.0


def wait_for_light_sensors(timeout=5.0):
    """Like wait_ready_sensors, but gives up with a clear message instead of hanging forever."""
    for name, sensor, port in (("Left", left_light, LEFT_LIGHT_PORT),
                               ("Right", right_light, RIGHT_LIGHT_PORT)):
        print(f"Waiting for {name.lower()} light sensor on port {port}...")
        start = time.time()
        while sensor.get_status() != "VALID_DATA":
            if time.time() - start > timeout:
                print(f"{name} light sensor on port {port} is not responding "
                      f"(status: {sensor.get_status()}). Check the cable / port number.")
                return False
            time.sleep(0.05)
    print("Light sensors ready.")
    return True


def read_light(sensor):
    """Brightness under the sensor (higher = brighter), or None on a bad reading."""
    if isinstance(sensor, NXTColorSensor):
        rgb = sensor.get_rgb()
        return None if None in rgb else sum(rgb)
    return sensor.get_red()


def average_red(sensor, samples=20, timeout=3.0):
    readings = []
    start = time.time()
    while len(readings) < samples:
        if time.time() - start > timeout:
            raise RuntimeError(f"Light sensor on port {sensor.port} returned no readings.")
        value = read_light(sensor)
        if value is not None:
            readings.append(value)
        time.sleep(0.01)
    return sum(readings) / len(readings)


def calibrate_light():
    """Sample the wood under each sensor at the start, so the threshold adapts to lighting."""
    global left_wood, right_wood, left_threshold, right_threshold
    left_wood = average_red(left_light)
    right_wood = average_red(right_light)
    left_threshold = left_wood * LEFT_LINE_RATIO
    right_threshold = right_wood * RIGHT_LINE_RATIO
    print(f"Wood: left = {left_wood:.1f}, right = {right_wood:.1f}   "
          f"Line thresholds: left = {left_threshold:.1f}, right = {right_threshold:.1f}")


def on_line(sensor, threshold):
    value = read_light(sensor)
    return value is not None and value < threshold


darkest = {}   # darkest reading of each sensor during the current line search, as % of its wood


def on_line_tracked(name, sensor, threshold, wood):
    """on_line(), but also remembers the darkest reading (for the 'missed' diagnostic)."""
    value = read_light(sensor)
    if value is None:
        return False
    darkest[name] = min(darkest.get(name, 999), 100 * value / wood)
    return value < threshold


def sensor_distance_to(axis, sign, line):
    """How far (cm) the sensors still are from line along the direction of travel (negative = past it)."""
    cx, cy, _ = get_odometer()
    pos = cy if axis == "y" else cx
    return (line - (pos + sign * SENSOR_OFFSET)) * sign


def along(axis, sign):
    """Axle position measured in the direction of travel (grows as the robot drives forward)."""
    cx, cy, _ = get_odometer()
    return (cy if axis == "y" else cx) * sign


def drive_through_line(heading, axis, sign, line):
    """
    Drive straight over the grid line at position `line` WITHOUT stopping or pivoting.
    Records where (in odometer distance) each sensor crosses the line:
      - both crossed  -> fix position along the path AND theta
                         (the gap between the two crossings tells how crooked the robot is)
      - one crossed   -> fix position only (the other sensor is riding a parallel line,
                         is over the board edge, or missed it)
      - none          -> odometry only
    Only a wood -> dark change counts as a crossing, so a sensor sitting on a line
    parallel to the path (or on the dark floor past the board edge) is ignored.
    """
    left_armed = right_armed = False     # sensor has seen wood inside the search window
    left_dark_from = right_dark_from = None   # where the current dark stretch started
    left_hit = right_hit = None          # along-track axle position where each sensor reached the line
    darkest.clear()

    while True:
        remaining = sensor_distance_to(axis, sign, line)
        if remaining > LINE_WINDOW:      # far from the line: full speed, ignore the sensors
            set_speeds(*hold_heading(heading, FORWARD_SPEED))
            time.sleep(0.005)
            continue

        pos = along(axis, sign)
        # A line counts only if the sensor goes wood -> dark and STAYS dark for LINE_CONFIRM_DIST cm.
        # The hit is recorded where the dark stretch started (the line's edge).
        if left_hit is None:
            hit = on_line_tracked("left", left_light, left_threshold, left_wood)
            if not hit:
                left_armed, left_dark_from = True, None
            elif left_armed:
                if left_dark_from is None:
                    left_dark_from = pos
                elif pos - left_dark_from >= LINE_CONFIRM_DIST:
                    left_hit = left_dark_from
        if right_hit is None:
            hit = on_line_tracked("right", right_light, right_threshold, right_wood)
            if not hit:
                right_armed, right_dark_from = True, None
            elif right_armed:
                if right_dark_from is None:
                    right_dark_from = pos
                elif pos - right_dark_from >= LINE_CONFIRM_DIST:
                    right_hit = right_dark_from

        if left_hit is not None and right_hit is not None:
            break
        first = left_hit if left_hit is not None else right_hit
        if first is not None and pos - first > MAX_HIT_GAP:
            break                        # the second sensor isn't going to cross
        if remaining < -LINE_SLACK:
            break                        # nothing seen: missed the line

        set_speeds(*hold_heading(heading, SLOW_SPEED))
        time.sleep(0.002)

    # Where the axle SHOULD have been when the sensors were on the line
    true_pos = line * sign - SENSOR_OFFSET

    if left_hit is None and right_hit is None:
        print(f"Missed the line at {axis} = {line:.1f}, using odometry only.")
        return

    # A hit that would move the odometer by more than MAX_POS_FIX is a false reading (wood grain, dirt)
    if left_hit is not None and abs(true_pos - left_hit) > MAX_POS_FIX:
        print(f"Line at {axis} = {line:.1f}: LEFT reading looks false, ignoring it.")
        left_hit = None
    if right_hit is not None and abs(true_pos - right_hit) > MAX_POS_FIX:
        print(f"Line at {axis} = {line:.1f}: RIGHT reading looks false, ignoring it.")
        right_hit = None
    if left_hit is None and right_hit is None:
        print(f"Line at {axis} = {line:.1f}: no good reading, using odometry only.")
        return

    hits = [h for h in (left_hit, right_hit) if h is not None]
    error = true_pos - sum(hits) / len(hits)          # how far off the odometer was, along the path
    cx, cy, _ = get_odometer()
    if axis == "y":
        set_odometer(new_y=cy + sign * error)
    else:
        set_odometer(new_x=cx + sign * error)

    if len(hits) == 1:
        side = "LEFT" if left_hit is not None else "RIGHT"
        print(f"Line at {axis} = {line:.1f}: only {side} sensor crossed. "
              f"Position fixed by {error:+.1f} cm, theta kept.")
        return

    # Right sensor crossing later than the left = robot is turned clockwise
    crooked = math.degrees(math.atan((right_hit - left_hit) / SENSOR_SPACING))
    if abs(crooked) > MAX_ANGLE_FIX:
        print(f"Line at {axis} = {line:.1f}: angle {crooked:+.1f} deg looks wrong, position fixed only.")
        return
    # Move theta only part of the way toward the measured value, so one noisy reading can't steer us off
    _, _, t = get_odometer()
    measured = heading + crooked + ALIGN_TRIM
    diff = (measured - t + 540) % 360 - 180
    set_odometer(new_theta=t + ANGLE_GAIN * diff)
    print(f"Line at {axis} = {line:.1f}: position fixed by {error:+.1f} cm, "
          f"robot is {crooked:+.1f} deg off, theta corrected.")


def correct_on_line(heading, axis, sign, line):
    """
    Robot is square to the grid line at position `line`: snap theta to the leg's
    heading and snap the coordinate along the direction of travel to match the line.
    """
    axle_pos = line - sign * SENSOR_OFFSET   # axle is SENSOR_OFFSET behind the sensors
    theta = heading + ALIGN_TRIM             # where the robot really points after lining up
    if axis == "y":
        set_odometer(new_y=axle_pos, new_theta=theta)
    else:
        set_odometer(new_x=axle_pos, new_theta=theta)


def correct_position_only(axis, sign, line):
    """One sensor is on the line: fix the coordinate along the path, leave theta alone."""
    axle_pos = line - sign * SENSOR_OFFSET
    if axis == "y":
        set_odometer(new_y=axle_pos)
    else:
        set_odometer(new_x=axle_pos)


# ============================ SQUARE ============================

# (heading, axis of travel, direction along that axis, the 3 grid lines crossed in order)
LINES_UP = [0.0, TILE, 2 * TILE]
LEGS = [
    (0, "y", +1, LINES_UP),                  # up
    (90, "x", +1, LINES_UP),                 # right
    (180, "y", -1, LINES_UP[::-1]),          # down
    (270, "x", -1, LINES_UP[::-1]),          # left, back to S
]


def square_driver():
    """Drive the 3x3-tile square from S, correcting at every grid line."""
    for heading, axis, sign, lines in LEGS:
        print(f"--- Leg heading {heading} deg ---")
        turn_to(heading)
        for i, line in enumerate(lines):
            drive_through_line(heading, axis, sign, line)
            if i < len(lines) - 1:
                drive_distance(LINE_CLEAR, heading)
        # Finish the leg at the centre of the corner tile, half a tile past the last line
        drive_until(axis, lines[-1] + sign * TILE / 2, sign, heading)


# ============================ TUNING TESTS ============================

def run_tuning_test():
    """Short runs used to tune WHEEL_RADIUS ("straight") and TRACK ("turn")."""
    init_odometer(0.0, 0.0, 0.0)
    odo_running.set()
    threading.Thread(target=odometer_loop, daemon=True).start()
    try:
        if MODE == "straight":
            print("Driving 2 tiles (60.96 cm) forward. Measure how far it really went.")
            drive_distance(2 * TILE, 0)
        else:
            print("Turning 4 x 90 deg. It should end facing exactly the way it started.")
            for heading in (90, 180, 270, 0):
                turn_to(heading)
                time.sleep(0.5)
    finally:
        stop()
        odo_running.clear()
        time.sleep(0.05)
        update_odometer()
        with odo_lock:
            print_pose("FINAL: ")
        reset_brick()


def run_sensor_test():
    """Motors float; print both light readings so lines can be checked by hand."""
    left_motor.float_motor()
    right_motor.float_motor()
    if not wait_for_light_sensors():
        return
    print("Keep both sensors on plain wood for calibration...")
    calibrate_light()
    print("Now slide the robot slowly over a line. Each sensor should say LINE on it, wood off it.")
    def describe(value, wood, threshold):
        if value is None:
            return "  no reading      "
        state = "LINE" if value < threshold else "wood"
        return f"{value:6.1f} = {100 * value / wood:4.0f}% of wood  {state}"

    while True:
        lv, rv = read_light(left_light), read_light(right_light)
        print(f"LEFT {describe(lv, left_wood, left_threshold)}   |   "
              f"RIGHT {describe(rv, right_wood, right_threshold)}")
        time.sleep(0.2)


def run_raw_sensor_test():
    """Motors float; print only the raw readings of both light sensors, nothing else."""
    left_motor.float_motor()
    right_motor.float_motor()
    if not wait_for_light_sensors():
        return

    def describe(sensor, kind, port):
        label = f"({kind}, port {port})"
        if isinstance(sensor, NXTColorSensor):
            rgb = sensor.get_rgb()
            if None in rgb:
                return f"{label} no reading"
            r, g, b = rgb
            return f"{label} R = {r:4.0f}  G = {g:4.0f}  B = {b:4.0f}  sum = {r + g + b:4.0f}"
        red = sensor.get_red()
        return f"{label} no reading" if red is None else f"{label} red = {red:5.1f}"

    while True:
        print(f"LEFT {describe(left_light, LEFT_LIGHT_TYPE, LEFT_LIGHT_PORT)}   |   "
              f"RIGHT {describe(right_light, RIGHT_LIGHT_TYPE, RIGHT_LIGHT_PORT)}")
        time.sleep(0.2)


# ============================ MAIN ============================

def main():
    if MODE == "float":
        init_odometer(0.0, 0.0, 0.0)
        print("Motors floating. Push the robot by hand.")
        float_motors()
        return

    if MODE in ("straight", "turn"):
        run_tuning_test()
        return

    if MODE == "sensors":
        run_sensor_test()
        return

    if MODE == "raw":
        run_raw_sensor_test()
        return

    print("Square mode: starting up.")
    if not wait_for_light_sensors():
        reset_brick()
        return
    calibrate_light()
    init_odometer(START_X, START_Y, START_THETA)
    odo_running.set()
    threading.Thread(target=odometer_loop, daemon=True).start()

    try:
        print("Driving the square.")
        square_driver()
    finally:
        stop()
        odo_running.clear()
        time.sleep(0.05)
        update_odometer()
        with odo_lock:
            print_pose("FINAL: ")
        reset_brick()


if __name__ == "__main__":
    main()