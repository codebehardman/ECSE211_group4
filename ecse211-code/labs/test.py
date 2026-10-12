from utils.brick import reset_brick, wait_ready_sensors, Motor
import time

motor = Motor("C")

if __name__ == "__main__":
    # wait for sensors to start up
    wait_ready_sensors()
    
    try:
        initial_encoder = motor.get_encoder()
        final_encoder = initial_encoder + 90
        
        # slower is more precise
        motor.set_dps(20)
        
        while motor.get_encoder() < final_encoder:
            time.sleep(0.01)
        
        initial_encoder = motor.get_encoder()
        final_encoder = initial_encoder - 90
        
        motor.set_dps(-20)
        
        while (motor.get_encoder() > final_encoder):
            time.sleep(0.01)
        
        
        print("Hello")
    except BaseException:
        reset_brick()
        exit()
    
    # reset brick to prevent motors/sensors from malfunctioning the next time we run a script
    reset_brick()
  