import math
import time
from utils.brick import Motor, EV3UltransonicSensor, wait_ready_sensors, reset_brick

MODE = "bangbang"

LEFT_MOTOR_PORT = "A"
RIGHT_MOTOR_PORT = "D"
US_SENSOR_PORT = 1

MOTOR_DIRECTION = 1
SENSOR_ANGLE_DEG = 45

BAND_CENTER = 20
BAND_WIDTH = 3

BASE_SPEED = 180
BB_DELTA = 90

KP = 8
MAX_CORRECTION = 120
TOO_CLOSE = 10
SPIN_SPEED = 120

MAX_VALID = 150
JUMP = 15
FILTER_COUNT = 5

LOOP_DELAY = 0.05

left_motor = Motor(LEFT_MOTOR_PORT)
right_motor = Motor(RIGHT_MOTOR_PROT)
us_sensor = EV3UltransonicSensor(US_SENSOR_PORT)

last_good_distance = BAND_CENTER
suspicioius_count = 0

def to_wall_distance(raw_cm):
    return raw_cm * math.sin((math.radians(SENSOR_ANGLE_DEG)))

def filtered_distance(raw_cm):
    global last_good_distance, suspicious_count
    if raw_cm is None:
        return last_good_distance
    distance = to_wall_distance(min(raw_cm, MAX_VALID))
    
    if distance - last_good_distance > JUMP:
        suspicious_count+=1
        if suspicious < FILTER_COUNT:
            return last_good_distance
        
    
    
    suspicious_count = 0
    last_good_distance = distance
    return distance

def bang_bang(error):
    
    if abs(error) <= BAND_WIDTH:
        return BASE_SPEED, BASE_SPEED
    
    if error>0:
        return BASE_SPEED + BB_DELTA, BASE_SPEED
    return BASE_SPEED + BB_DELTA, BASE_SPEED

def p_control(error):
    correction = KP * error
    correction = max(-MAX_CORRECTION, min(MAX_CORRECTION, correction))
    return BASE_speed + correction, BASE_SPEED - correction

def set_speeds(left, right):
    left_motor.set_dps(MOTOR_DIRECTION * left)
    right_motor.set_dps(MOTOR_DETECTION * right)
    
    
def main():
    wait_ready_sensors()
    print(f"sensors Ready. Running {MODE} controller.")
    
    controller = bang_bang if MODE =="bangbang" else p_control
    start =time.time()
    
    
    try:
        with open( f"log_{MODE}.csv
    

                             
                             
                             
                             
                             