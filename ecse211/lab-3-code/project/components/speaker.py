from utils import sound
from utils.sound import NOTES
import time

"""
Speaker Component
Handles audio output for the digital flute
"""

class Speaker:
    def __init__(self, default_pitch="A4", default_duration=0.2):
        self.SPEAKER = sound.Sound(duration=default_duration, pitch=default_pitch, volume=60)
        print("Initialized speaker")
        
    def play_note(self, note: str):
        print("Playing note")

        try:
            self.SPEAKER.set_pitch(NOTES[note])
            self.SPEAKER.update_audio()
            self.SPEAKER.play()
                
        except KeyboardInterrupt:
            print("\nCode interrupted")
            self.__stop_note()

    def __stop_note(self):
        self.SPEAKER.stop()
        print("Stopping speaker")
    
    def cleanup(self):
        self.__stop_note()