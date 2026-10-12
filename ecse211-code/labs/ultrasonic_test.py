from utils.brick import reset_brick, wait_ready_sensors, Motor, EV3UltrasonicSensor
import time

us_sensor = EV3UltrasonicSensor(1)
if __name__ == "__main__":
    # wait for sensors to start up
    wait_ready_sensors()
    
    try:
        while(True):
            d = us_sensor.get_cm()
            print(d)
            time.sleep(0.1)
    except BaseException:
        reset_brick()
        exit()
    
    # reset brick to prevent motors/sensors from malfunctioning the next time we run a script
    reset_brick()
  
