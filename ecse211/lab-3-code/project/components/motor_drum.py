from utils.brick import Motor
from config.settings import PORT_MOTOR
import time
import threading

"""
DrumMotor Component
Controls the pace of the motor moving the rod
"""

class DrumMotor:
    def __init__(self, default_tempo=120):
        self.tempo = default_tempo

        self.MOTOR = Motor(PORT_MOTOR)
        self.__initialize_motor()

        self.drum_running = False
        self.stop_event = None
        self.drum_thread = None
        print("Initialized motor")

    def __initialize_motor(self):
        # Reset encoder to set current position as 0 degrees
        self.MOTOR.reset_encoder()
        self.MOTOR.set_limits(dps=360)

    def start_drumming_loop(self, stop_event=None):
        self.stop_event = stop_event if stop_event is not None else threading.Event()
        self.drum_running = True
        self.drum_thread = threading.Thread(target=self.__drumming_worker, daemon=True)
        self.drum_thread.start()
        print("Starting drumming")

    def __drumming_worker(self):
        rest_amount = 60 / self.tempo
        try:
            while not self.stop_event.is_set():
                # Move forward 90 degrees
                self.MOTOR.set_position_relative(90)
                if self.stop_event.wait(rest_amount):
                    break

                # Move backward 90 degrees
                self.MOTOR.set_position_relative(-90)
                if self.stop_event.wait(rest_amount):
                    break
        except BaseException as e:
            print(f"Drum: {e}\n")
        finally:
            self.__stop_drumming()

    def __stop_drumming(self):
        self.drum_running = False
        if self.stop_event:
            self.stop_event.set()
        self.MOTOR.set_position_relative(0)
        print("Stopping drumming")

    def cleanup(self):
        self.__stop_drumming()
        if self.drum_thread and self.drum_thread.is_alive():
            self.drum_thread.join(timeout=2)