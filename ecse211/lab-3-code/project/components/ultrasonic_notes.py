from utils.brick import EV3UltrasonicSensor
from config.settings import PORT_ULTRASONIC, DISTANCE_NOTE_MAP

"""
Ultrasonic Component
Determines the pitch played on the speaker
"""

class UltrasonicNoteReader:
    def __init__(self):
        self.US_SENSOR = EV3UltrasonicSensor(PORT_ULTRASONIC)
        print("Initialized US sensor")

    def get_note(self):
        distance = self.US_SENSOR.get_value()
        
        if distance is None:
            return None
        
        # return note corresponding to the distance
        for (min_dist, max_dist), note in DISTANCE_NOTE_MAP.items():
            if min_dist <= distance < max_dist:
                return note