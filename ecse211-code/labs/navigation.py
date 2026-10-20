#!/usr/bin/env python3
"""
ECSE 211 - Lab 3: Navigation

Drives through WAYPOINTS (in tiles) starting from the origin (0, 0), facing +y.

Modes:
  "safest"   -> travel in x, then in y, to each waypoint. Every grid line crossed
                is used to square the robot up and reset its position (Lab 2 correction).
  "shortest" -> turn the minimal angle towards each waypoint and drive straight to it.

No odometer thread: every move is a measured turn or straight drive using the
wheel encoders, and the robot keeps track of where it is from the moves it made.
In "safest" mode that position is overwritten every time both light sensors
line up on a grid line, so encoder errors never build up over more than one tile.

Conventions (same as Lab 2):
  - heading is compass-style: 0 = facing +y, measured CLOCKWISE.
  - Left wheel forward + right wheel backward -> heading increases.

Stop with Ctrl+C.
"""

import atexit
import math
import signal
import sys
import time
from utils.brick import Motor, EV3ColorSensor, NXTColorSensor, reset_brick


# ============================ SETTINGS ============================

MODE = "safest"          # "safest" or "shortest"

# Waypoints in TILES, visited in order. The TA gives these at the demo.
WAYPOINTS = [
    (1, 1),
    (2, 0),
    (2, 2),
    (0, 2),
]

# --- Hardware (same as odometry.py) ---
LEFT_MOTOR_PORT = "D"
RIGHT_MOTOR_PORT = "A"
LEFT_LIGHT_PORT = 2      # port of the sensor mounted on the robot's LEFT side (NXT)
RIGHT_LIGHT_PORT = 4     # port of the sensor mounted on the robot's RIGHT side (EV3)
LEFT_LIGHT_TYPE = "NXT"  # CHECK: "EV3" or "NXT" (printed on the sensor)
RIGHT_LIGHT_TYPE = "EV3" # CHECK: "EV3" or "NXT"
MOTOR_DIRECTION = 1      # motors flipped around after Lab 2 (was -1)

# --- Robot geometry (same values as odometry.py, tune there with "straight"/"turn") ---
WHEEL_RADIUS = 2.10      # cm
RIGHT_WHEEL_SCALE = 1.0  # right wheel's effective size / left wheel's
TRACK = 14.8             # cm, distance between the two wheels' contact points
SENSOR_OFFSET = 39       # cm, how far AHEAD of the wheel axle the light sensors sit. CHECK: measure this

# --- Board ---
TILE = 30.48             # cm
GRID_LINES = [0, 1, 2]   # CHECK: tile numbers of the black lines on the board (same numbering as the
                         # waypoints). Lab 2 used lines at 0, 1 and 2 tiles from the origin.

# --- Motion ---
FORWARD_SPEED = 150      # deg/s
SLOW_SPEED = 70          # deg/s, speed near a line and for the last few cm
TURN_SPEED = 100         # deg/s
TURN_SLOW_SPEED = 40     # deg/s, last few degrees of a turn
TURN_SLOW_ZONE = 15.0    # deg, slow down for the last this many degrees of a turn
TURN_TOLERANCE = 0.5     # deg, a turn is done when within this of the target
SLOW_ZONE = 3.0          # cm, slow down for the last this many cm of a straight drive
KP_STRAIGHT = 3.0        # deg/s of wheel speed difference per degree of wheel encoder mismatch
MAX_STRAIGHT_CORR = 50   # deg/s, cap on the straight-line correction
MAX_LINE_WAIT = 2.0      # s, give up waiting for the second sensor after this
LINE_WINDOW = 8.0        # cm, start looking for a line once the sensors are this close to it
LINE_SLACK = 6.0         # cm, if no line is seen this far past where it should be, it was missed
MIN_LINE_GAP = 3.0       # cm, ignore a line that is already (almost) under the sensors at the start
ALIGN_TRIM = 0.0         # deg, how crooked the robot really is after lining up (see odometry.py)
PAUSE = 0.3              # s, pause between moves so the robot settles

# --- Light sensor (same values as odometry.py, tune there with "sensors"/"raw") ---
LEFT_LINE_RATIO = 0.97   # measured: wood sum ~1370 (1350-1388), line ~1296 (1286-1305) -> threshold ~1329
RIGHT_LINE_RATIO = 0.75  # measured: wood red ~22 (18-23), line ~13.5 (13-14) -> threshold ~16.5
LINE_CONFIRM = 2         # dark readings in a row needed before a line counts (filters noise)

# ==================================================================


left_motor = Motor(LEFT_MOTOR_PORT)
right_motor = Motor(RIGHT_MOTOR_PORT)


def make_light_sensor(port, kind):
    if kind.upper() == "NXT":
        return NXTColorSensor(port)               # NXT only supports component (RGB) mode
    return EV3ColorSensor(port, mode="red")


# Light sensors are only needed for the safest path
USES_LIGHT = MODE == "safest"
left_light = make_light_sensor(LEFT_LIGHT_PORT, LEFT_LIGHT_TYPE) if USES_LIGHT else None
right_light = make_light_sensor(RIGHT_LIGHT_PORT, RIGHT_LIGHT_TYPE) if USES_LIGHT else None


def stop_robot(*_):
    reset_brick()
    print("Robot stopped.")
    sys.exit(0)


atexit.register(reset_brick)
signal.signal(signal.SIGINT, stop_robot)
signal.signal(signal.SIGTERM, stop_robot)


# ============================ POSITION ============================

# Where the robot believes its axle centre is (cm) and which way it faces (deg).
x, y, heading = 0.0, 0.0, 0.0


def wrap_angle(angle):
    """Keep an angle in [0, 360)."""
    angle %= 360
    return 0.0 if angle >= 360 else angle


def angle_to(target):
    """Signed degrees to turn from the current heading to target, in [-180, 180). Positive = clockwise."""
    return (target - heading + 540) % 360 - 180


def advance(dist):
    """Move the believed position dist cm along the current heading."""
    global x, y
    x += dist * math.sin(math.radians(heading))
    y += dist * math.cos(math.radians(heading))


def print_pose(prefix=""):
    shown = round(heading, 1) % 360   # never display 360.0
    print(f"{prefix}x = {x:7.2f} cm ({x / TILE:5.2f} tiles)   "
          f"y = {y:7.2f} cm ({y / TILE:5.2f} tiles)   heading = {shown:5.1f} deg")


# ============================ MOTION ============================

def read_encoders():
    """Encoder positions in degrees, positive = that wheel rolled forward."""
    return (MOTOR_DIRECTION * left_motor.get_encoder(),
            MOTOR_DIRECTION * right_motor.get_encoder())


def wheel_cm(enc_deg, scale=1.0):
    return math.radians(enc_deg) * WHEEL_RADIUS * scale


def set_speeds(left, right):
    left_motor.set_dps(MOTOR_DIRECTION * left)
    right_motor.set_dps(MOTOR_DIRECTION * right)


def stop():
    set_speeds(0, 0)
    time.sleep(PAUSE)


class Segment:
    """Encoder readings since the start of one straight drive."""

    def __init__(self):
        self.left0, self.right0 = read_encoders()

    def deltas(self):
        left, right = read_encoders()
        return left - self.left0, right - self.right0

    def distance(self):
        """cm the axle centre has moved forward since the start."""
        d_left, d_right = self.deltas()
        return (wheel_cm(d_left) + wheel_cm(d_right, RIGHT_WHEEL_SCALE)) / 2

    def straight_speeds(self, speed):
        """Wheel speeds that keep both wheels covering the same distance (drive straight)."""
        d_left, d_right = self.deltas()
        mismatch = d_left - d_right * RIGHT_WHEEL_SCALE      # > 0: left is ahead, robot drifting right
        correction = max(-MAX_STRAIGHT_CORR, min(MAX_STRAIGHT_CORR, KP_STRAIGHT * mismatch))
        return speed - correction, speed + correction


def drive_straight(dist):
    """Drive dist cm straight (negative = backwards), measured by the wheel encoders, and update the position."""
    if abs(dist) < 0.1:
        return
    direction = 1 if dist > 0 else -1
    seg = Segment()
    while True:
        remaining = abs(dist) - direction * seg.distance()
        if remaining <= 0:
            break
        speed = SLOW_SPEED if remaining < SLOW_ZONE else FORWARD_SPEED
        set_speeds(*seg.straight_speeds(direction * speed))
        time.sleep(0.005)
    set_speeds(0, 0)
    advance(seg.distance())
    time.sleep(PAUSE)


def turn_by(angle):
    """Turn in place by angle degrees (positive = clockwise), measured by the wheel encoders."""
    global heading
    if abs(angle) < TURN_TOLERANCE:
        return
    # Each wheel travels along a circle of diameter TRACK: arc = angle * TRACK / 2
    target = math.degrees(math.radians(abs(angle)) * TRACK / 2 / WHEEL_RADIUS)   # wheel degrees
    tolerance = target * TURN_TOLERANCE / abs(angle)
    slow_zone = target * TURN_SLOW_ZONE / abs(angle)
    direction = 1 if angle > 0 else -1
    left0, right0 = read_encoders()
    while True:
        left, right = read_encoders()
        turned = (abs(left - left0) + abs(right - right0)) / 2
        remaining = target - turned
        if remaining <= tolerance:
            break
        speed = TURN_SLOW_SPEED if remaining < slow_zone else TURN_SPEED
        set_speeds(direction * speed, -direction * speed)   # left fwd, right back -> clockwise
        time.sleep(0.005)
    set_speeds(0, 0)
    heading = wrap_angle(heading + angle)
    time.sleep(PAUSE)


def turn_to(target):
    """Turn to face target heading, whichever way is shorter (minimal angle)."""
    turn_by(angle_to(target))


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


def average_light(sensor, samples=20, timeout=3.0):
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
    left_wood = average_light(left_light)
    right_wood = average_light(right_light)
    left_threshold = left_wood * LEFT_LINE_RATIO
    right_threshold = right_wood * RIGHT_LINE_RATIO
    print(f"Wood: left = {left_wood:.1f}, right = {right_wood:.1f}   "
          f"Line thresholds: left = {left_threshold:.1f}, right = {right_threshold:.1f}")


def on_line(sensor, threshold):
    value = read_light(sensor)
    return value is not None and value < threshold


def set_axis(axis, value):
    global x, y
    if axis == "x":
        x = value
    else:
        y = value


def get_axis(axis):
    return x if axis == "x" else y


def drive_to_line(axis, sign, line):
    """
    Drive forward until both sensors sit on the grid line at position `line` (cm).
    The wheel whose sensor hits first stops; the other keeps going slowly until
    its sensor hits too, which squares the robot up with the line. The position
    along the axis and the heading are then reset from the line.
    Sensors are only watched near where the line should be, and if nothing is
    seen LINE_SLACK cm past it, the line counts as missed.
    """
    global heading
    leg_heading = heading
    seg = Segment()
    to_line = (line - sign * SENSOR_OFFSET - get_axis(axis)) * sign   # axle travel until sensors reach it
    left_done = right_done = False
    left_dark = right_dark = 0
    first_hit_time = None

    while not (left_done and right_done):
        if first_hit_time is None:
            remaining = to_line - seg.distance()
            if remaining < -LINE_SLACK:
                print(f"Missed the line at {axis} = {line / TILE:.0f} tiles, using the encoders only.")
                break
            if remaining > LINE_WINDOW:            # too far away, ignore dark spots in the wood
                set_speeds(*seg.straight_speeds(FORWARD_SPEED))
                time.sleep(0.005)
                continue

        if not left_done:
            left_dark = left_dark + 1 if on_line(left_light, left_threshold) else 0
            left_done = left_dark >= LINE_CONFIRM
        if not right_done:
            right_dark = right_dark + 1 if on_line(right_light, right_threshold) else 0
            right_done = right_dark >= LINE_CONFIRM

        if (left_done or right_done) and first_hit_time is None:
            first_hit_time = time.time()
        if first_hit_time and time.time() - first_hit_time > MAX_LINE_WAIT:
            missed = "RIGHT" if left_done else "LEFT"
            print(f"{missed} sensor missed the line at {axis} = {line / TILE:.0f} tiles. Skipping alignment.")
            break

        if not (left_done or right_done):
            set_speeds(*seg.straight_speeds(SLOW_SPEED))         # near the line: creep straight
        else:
            set_speeds(0 if left_done else SLOW_SPEED, 0 if right_done else SLOW_SPEED)
        time.sleep(0.002)

    set_speeds(0, 0)
    if left_done and right_done:
        set_axis(axis, line - sign * SENSOR_OFFSET)   # axle is SENSOR_OFFSET behind the sensors
        heading = wrap_angle(leg_heading + ALIGN_TRIM)
        print(f"Lined up on the line at {axis} = {line / TILE:.0f} tiles, position corrected.")
    else:
        advance(seg.distance())
    time.sleep(PAUSE)


# ============================ NAVIGATION ============================

def travel_axis(axis, target):
    """Safest path, one leg: drive along x or y only to target (cm), correcting at every line."""
    start = get_axis(axis)
    if abs(target - start) < 0.5:
        return
    sign = 1 if target > start else -1
    if axis == "y":
        turn_to(0 if sign > 0 else 180)
    else:
        turn_to(90 if sign > 0 else 270)

    # Lines the SENSORS will cross on the way (they run SENSOR_OFFSET ahead of the axle)
    sensor_start = start + sign * SENSOR_OFFSET
    sensor_end = target + sign * SENSOR_OFFSET
    lines = sorted((n * TILE for n in GRID_LINES
                    if (n * TILE - sensor_start) * sign > MIN_LINE_GAP
                    and (sensor_end - n * TILE) * sign >= 0),
                   key=lambda pos: pos * sign)
    for line in lines:
        drive_to_line(axis, sign, line)

    # Last bit from the last line (or from the start) with the encoders
    drive_straight((target - get_axis(axis)) * sign)


def go_safest(wx, wy):
    travel_axis("x", wx)
    travel_axis("y", wy)


def go_shortest(wx, wy):
    """Shortest path: turn the minimal angle to face the waypoint, then drive straight to it."""
    dx, dy = wx - x, wy - y
    dist = math.hypot(dx, dy)
    if dist < 0.5:
        return
    turn_to(math.degrees(math.atan2(dx, dy)))      # compass heading: 0 = +y, clockwise
    drive_straight(dist)


# ============================ MAIN ============================

def main():
    print(f"{MODE.capitalize()} path through {len(WAYPOINTS)} waypoints: {WAYPOINTS}")
    if USES_LIGHT:
        if not wait_for_light_sensors():
            reset_brick()
            return
        calibrate_light()

    go = go_safest if MODE == "safest" else go_shortest
    try:
        for i, (tx, ty) in enumerate(WAYPOINTS, 1):
            print(f"--- Waypoint {i}: ({tx}, {ty}) ---")
            go(tx * TILE, ty * TILE)
            print_pose(f"Reached waypoint {i}: ")
    finally:
        set_speeds(0, 0)
        print_pose("FINAL: ")
        reset_brick()


if __name__ == "__main__":
    main()
