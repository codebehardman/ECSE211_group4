from utils.brick import TouchSensor
from config.settings import PORT_TOUCH_SENSOR_START, PORT_TOUCH_SENSOR_STOP

"""
TouchSensors Component
Controls the start and emergency stop
"""

class TouchSensors:
    def __init__(self):
        self.START_SENSOR = TouchSensor(PORT_TOUCH_SENSOR_START)
        self.STOP_SENSOR = TouchSensor(PORT_TOUCH_SENSOR_STOP)
        
        print("Initialized start and stop touch sensors")
      
    def start_pressed(self):
        if (self.START_SENSOR.is_pressed()):
            return True
        return False
    
    def stop_pressed(self):
        if (self.STOP_SENSOR.is_pressed()):
            return True
        return False