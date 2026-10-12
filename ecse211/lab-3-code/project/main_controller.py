from components.motor_drum import DrumMotor
from components.speaker import Speaker
from components.touch_sensors import TouchSensors
from components.ultrasonic_notes import UltrasonicNoteReader
from utils.brick import wait_ready_sensors, reset_brick
import threading
import time

"""
Controller for hardware components of digital flute
"""

# Initialize hardware
drum = DrumMotor()
speaker = Speaker()
touch = TouchSensors()
note_reader = UltrasonicNoteReader()
wait_ready_sensors()

print("Finished initialization.")

def start_program():
    try:
        print("Waiting for start button press...")
        while not touch.start_pressed():
            time.sleep(0.1)
        run_digital_flute()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        reset_brick()
        exit()

def run_digital_flute():
    stop_event = threading.Event()

    try:
        drum.start_drumming_loop(stop_event)

        while not stop_event.is_set():
            if touch.stop_pressed():
                stop_event.set()
                break

            # play note based on ultrasonic reading
            note = note_reader.get_note()
            if note:
                speaker.play_note(note)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_event.set()
    finally:
        drum.cleanup()
        speaker.cleanup()
        reset_brick()
        exit()

if __name__ == "__main__":
    start_program()