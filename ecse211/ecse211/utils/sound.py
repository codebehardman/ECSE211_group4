#!/usr/bin/env python3

"""
Sound module for the BrickPi3.

See the bottom of this file for usage examples.

Authors: Ryan Au, Younes Boubekeur
"""

from typing import Iterable, SupportsIndex, Tuple, overload
from time import time, sleep
from typing import Tuple
import simpleaudio as sa
import math
import os
import pickle
import functools

print("Initializing sound module")


BASE_SOUND = lambda x, freq: [math.sin(2 * math.pi * freq * i) for i in x]


def linspace(fs, n):
    return [i / fs for i in range(0, n)]


def sin_gen(freq, factor):
    return lambda x: math.sin(2 * math.pi * x * freq) * factor


def freq_modulator(mod=440.0, k=1.0):
    if type(k) == float or type(k) == int:
        strength = lambda x: k
    elif type(k) == str:
        if k in NOTE:
            strength = lambda x: NOTE[k]

    def instrument(x, freq):
        carrier = [2 * math.pi * i * mod for i in x]
        modulator = [strength(i) * math.sin(2 * math.pi * i * freq) for i in x]
        res = [math.cos(c + m) for c, m in zip(carrier, modulator)]
        maximum = max(map(abs, res))
        return [r / maximum for r in res]
    return instrument


@functools.lru_cache
def gen_custom_freq(frequency=440, seconds=1, vol_factor=0.2, fs=8000,
                    instrument=None, instrument_strength=1.0, cutoff_factor=0.01):
    """
    Generate a byte-string of a sin-wave based sound (default), given a frequency, time, and volume.
    instrument is a function with two inputs, x for time, and frequency for what the frequency is.
    """
    if type(instrument) == str:
        if instrument in NOTE:
            instrument = freq_modulator(NOTE[instrument], instrument_strength)
        else:
            instrument = None
    elif type(instrument) == float or type(instrument) == int:
        instrument = freq_modulator(abs(instrument), instrument_strength)

    if instrument is None:
        instrument = BASE_SOUND

    n = int(seconds * fs)
    t = [i / fs for i in range(0, n)]

    note = instrument(t, frequency)
    maximum = max(map(abs, note))

    audio = [int(i * vol_factor * (2**15 - 1)) / maximum for i in note]
    dynamics = [1 for i in range(0, n)]
    cutoff = min(len(audio), int(fs * cutoff_factor))
    k = (1 / 3) * (1 / math.log(2))
    for i in range(cutoff):
        x = math.log(i / cutoff * 7 + 1) * k
        dynamics[n - i - 1] = x
        dynamics[i] = x
    audio = b''.join([int(a * d).to_bytes(2, "little", signed=True) for a, d in zip(audio, dynamics)])
    return audio


def play_freq(frequency=440, seconds=1, vol_factor=0.2, fs=8000,
              bg_play=False, instrument=None, instrument_strength=1.0):
    "Play a sound given frequency, time, and volume."
    audio = gen_custom_freq(
        frequency,
        seconds,
        vol_factor,
        fs,
        instrument=instrument,
        instrument_strength=instrument_strength)
    play_obj = sa.play_buffer(audio, 1, 2, fs)
    return play_obj if bg_play else play_obj.wait_done()


def play_many_freq(frequencies: list[Tuple[int, float, float]], fs=8000,
                   bg_play=False, instrument=None, instrument_strength=1.0):
    """
    Play many frequencies. Accepts a list of 3-length tuplets, each consisting of (freq, sec, vol).
    freq is in Hz or Hertz
    sec uses seconds
    vol is a scale from 0 to 1
    """
    audio = b"".join([gen_custom_freq(f, s, v, fs, instrument=instrument,
                     instrument_strength=instrument_strength) for f, s, v in frequencies])
    play_obj = sa.play_buffer(audio, 1, 2, fs)
    return play_obj if bg_play else play_obj.wait_done()


def play_many_notes(notes: list[Tuple[str, float, float]], fs=8000,
                    bg_play=False, instrument=None, instrument_strength=1.0):
    """
    Play many notes. Accepts a list of 3-length tuplets, each consisting of (note, sec, vol).
    notes such as "A4" or "Bb2"
    sec uses seconds
    vol is a scale from 0 to 1
    """
    audio = b"".join([gen_custom_freq(NOTE[n], s, v, fs, instrument=instrument,
                     instrument_strength=instrument_strength) for n, s, v in notes])
    play_obj = sa.play_buffer(audio, 1, 2, fs)
    return play_obj if bg_play else play_obj.wait_done()


def play_note(note_name="A4", seconds=1, vol_factor=0.2, fs=8000,
              bg_play=False, instrument=None, instrument_strength=1.0):
    """
    Play a sound given note name, time, and volume.

    Sound will play on its own thread, separate from the main thread.
    Sound will stop when the main thread exits.

    If bg_play (background play) is True, play and return a sound object s, which has the following methods:
    -- s.wait_done(): pauses current thread until sound has stopped playing
    -- s.stop(): stops the sound from playing
    -- s.is_playing(): whether the sound is playing or not
    If bg_play is False, pauses current thread until sound has stopped playing then return None

    Note use the format A4, B4, C#2, Gb6...etc.
    Warning: there is no support for B#_, E#_, Cb_, or Fb_

    NOTE: Use play_many_notes() to get one continuous sound object s
    """
    play_obj = play_freq(
        NOTE[note_name],
        seconds,
        vol_factor,
        fs,
        bg_play=True,
        instrument=instrument,
        instrument_strength=instrument_strength)  # True to get the sound object
    return play_obj if bg_play else play_obj.wait_done()


NOTE = {
    "C0": 16.35,
    "D0": 18.35,
    "E0": 20.60,
    "F0": 21.83,
    "G0": 24.50,
    "A0": 27.50,
    "B0": 30.87,
    "C1": 32.70,
    "D1": 36.71,
    "E1": 41.20,
    "F1": 43.65,
    "G1": 49.00,
    "A1": 55.00,
    "B1": 61.74,
    "C2": 65.41,
    "D2": 73.42,
    "E2": 82.41,
    "F2": 87.31,
    "G2": 98.00,
    "A2": 110.00,
    "B2": 123.47,
    "C3": 130.81,
    "D3": 146.83,
    "E3": 164.81,
    "F3": 174.61,
    "G3": 196.00,
    "A3": 220.00,
    "B3": 246.94,
    "C4": 261.63,
    "D4": 293.66,
    "E4": 329.63,
    "F4": 349.23,
    "G4": 392.00,
    "A4": 440.00,
    "B4": 493.88,
    "C5": 523.25,
    "D5": 587.33,
    "E5": 659.25,
    "F5": 698.46,
    "G5": 783.99,
    "A5": 880.00,
    "B5": 987.77,
    "C6": 1046.50,
    "D6": 1174.66,
    "E6": 1318.51,
    "F6": 1396.91,
    "G6": 1567.98,
    "A6": 1760.00,
    "B6": 1975.53,
    "C7": 2093.00,
    "D7": 2349.32,
    "E7": 2637.02,
    "F7": 2793.83,
    "G7": 3135.96,
    "A7": 3520.00,
    "B7": 3951.07,
    "C8": 4186.01,
    "D8": 4698.63,
    "E8": 5274.04,
    "F8": 5587.65,
    "G8": 6271.93,
    "A8": 7040.00,
    "B8": 7902.13,
    "C#0": 17.32,
    "Db0": 17.32,
    "D#0": 19.45,
    "Eb0": 19.45,
    "F#0": 23.12,
    "Gb0": 23.12,
    "G#0": 25.96,
    "Ab0": 25.96,
    "A#0": 29.14,
    "Bb0": 29.14,
    "C#1": 34.65,
    "Db1": 34.65,
    "D#1": 38.89,
    "Eb1": 38.89,
    "F#1": 46.25,
    "Gb1": 46.25,
    "G#1": 51.91,
    "Ab1": 51.91,
    "A#1": 58.27,
    "Bb1": 58.27,
    "C#2": 69.30,
    "Db2": 69.30,
    "D#2": 77.78,
    "Eb2": 77.78,
    "F#2": 92.50,
    "Gb2": 92.50,
    "G#2": 103.83,
    "Ab2": 103.83,
    "A#2": 116.54,
    "Bb2": 116.54,
    "C#3": 138.59,
    "Db3": 138.59,
    "D#3": 155.56,
    "Eb3": 155.56,
    "F#3": 185.00,
    "Gb3": 185.00,
    "G#3": 207.65,
    "Ab3": 207.65,
    "A#3": 233.08,
    "Bb3": 233.08,
    "C#4": 277.18,
    "Db4": 277.18,
    "D#4": 311.13,
    "Eb4": 311.13,
    "F#4": 369.99,
    "Gb4": 369.99,
    "G#4": 415.30,
    "Ab4": 415.30,
    "A#4": 466.16,
    "Bb4": 466.16,
    "C#5": 554.37,
    "Db5": 554.37,
    "D#5": 622.25,
    "Eb5": 622.25,
    "F#5": 739.99,
    "Gb5": 739.99,
    "G#5": 830.61,
    "Ab5": 830.61,
    "A#5": 932.33,
    "Bb5": 932.33,
    "C#6": 1108.73,
    "Db6": 1108.73,
    "D#6": 1244.51,
    "Eb6": 1244.51,
    "F#6": 1479.98,
    "Gb6": 1479.98,
    "G#6": 1661.22,
    "Ab6": 1661.22,
    "A#6": 1864.66,
    "Bb6": 1864.66,
    "C#7": 2217.46,
    "Db7": 2217.46,
    "D#7": 2489.02,
    "Eb7": 2489.02,
    "F#7": 2959.96,
    "Gb7": 2959.96,
    "G#7": 3322.44,
    "Ab7": 3322.44,
    "A#7": 3729.31,
    "Bb7": 3729.31,
    "C#8": 4434.92,
    "Db8": 4434.92,
    "D#8": 4978.03,
    "Eb8": 4978.03,
    "F#8": 5919.91,
    "Gb8": 5919.91,
    "G#8": 6644.88,
    "Ab8": 6644.88,
    "A#8": 7458.62,
    "Bb8": 7458.62,
}

_note_order = {
    'b': 'x', '': 'y', '#': 'z',
    'C': '0', 'D': '1', 'E': '2', 'F': '3', 'G': '4', 'A': '5', 'B': '6', }

NOTE_NAMES = sorted(list(NOTE.keys()), key=lambda x: x[-1] + _note_order[x[0]] + _note_order[x[1:-1]])


class Sound():
    def __init__(self, pitch=440.0, seconds=1, vol_factor=0.2, fs=8000, bg_play=None,
                 instrument=None, instrument_strength=1.0, cutoff_factor=0.01, debug=False):
        if debug:
            print("Creating Sound", pitch, seconds, sep=',')
        self.set_pitch(pitch)
        self.set_instrument(instrument)
        self.set_volume(vol_factor)
        self.set_instrument_strength(instrument_strength)
        self.set_cutoff_factor(cutoff_factor)
        self.seconds = seconds
        self.fs = fs

        self.change_duration(seconds, fs)

        if bg_play is None:
            pass
        elif bg_play:
            self.play()
        elif not bg_play:
            self.play()
            self.wait_done()
        if debug:
            print("Done Creating Sound", pitch, seconds, sep=',')

    def set_pitch(self, pitch):
        if type(pitch) == str:
            if pitch in NOTE:
                self.pitch = NOTE[pitch]
        elif type(pitch) == int or type(pitch) == float:
            self.pitch = abs(pitch)
        else:
            self.pitch = pitch

    def set_instrument(self, instrument):
        if instrument is None:
            self.instrument = None
        elif type(instrument) == str:
            if instrument in NOTE:
                self.instrument = NOTE[instrument]
        elif type(instrument) == int or type(instrument) == float:
            self.instrument = abs(instrument)

    def set_instrument_strength(self, strength):
        self.instrument_strength = strength

    def set_volume(self, vol):
        self.vol_factor = vol

    def set_cutoff_factor(self, factor):
        self.cutoff_factor = factor

    def change_duration(self, seconds, fs=None):
        if self.is_playing():
            self.stop()
        self.player = None

        if fs is None:
            fs = self.fs
        self.size = int(seconds * fs)
        self.audio = bytearray(self.size * 2)
        self.seconds = seconds
        self.fs = fs
        self.update_audio()

    def update_audio(self):
        new_audio = gen_custom_freq(
            frequency=self.pitch,
            seconds=self.seconds,
            vol_factor=self.vol_factor,
            fs=self.fs,
            instrument=self.instrument,
            instrument_strength=self.instrument_strength)
        for i, a in enumerate(new_audio):
            self.audio[i] = a
        return self.audio

    def play(self):
        if self.is_playing():
            self.stop()
        self.player = sa.play_buffer(self.audio, 1, 2, self.fs)

    def stop(self):
        if getattr(self, 'player', None) is not None:
            self.player.stop()
            self.player = None

    def is_playing(self):
        if getattr(self, 'player', None) is not None:
            return self.player.is_playing()
        return False

    def wait_done(self):
        if getattr(self, 'player', None) is not None:
            self.player.wait_done()
            self.player = None

    def __len__(self):
        return self.size

    def __add__(self, other):
        if isinstance(other, Sound):
            return SoundSeq([self, other])
        elif isinstance(other, SoundSeq):
            return SoundSeq([self] + other.sounds)
        raise TypeError("Added value is of an invalid type. Must be Sound or SoundSeq.")

    def __mul__(self, factor):
        if type(factor) == int:
            return SoundSeq([self] * abs(factor))

    def __repr__(self):
        return f"""(freq={self.pitch}, s={self.seconds}, v={self.vol_factor}, rate={self.fs}, mod={
            self.instrument}, k={self.instrument_strength}, fade={self.cutoff_factor})"""


SOUNDS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sounds.pickle")

try:
    with open(SOUNDS_FILE, "rb") as f:
        print(f"Attempting to loading sounds from file {SOUNDS_FILE}")
        BASIC_SOUNDS, ORGAN_SOUNDS = pickle.load(f)
except (FileNotFoundError, AttributeError):
    print("Could not read sounds from file, so they will be computed. This might take some time...")
    BASIC_SOUNDS: dict[str, Sound] = {note: Sound(seconds=0.5, pitch=note, cutoff_factor=0.01) for note in NOTE_NAMES}
    ORGAN_SOUNDS: dict[str, Sound] = {note: Sound(
        seconds=0.5, pitch=note, cutoff_factor=0.01, instrument=1, instrument_strength=1) for note in NOTE_NAMES}
    with open(SOUNDS_FILE, "wb") as f:
        print(f"Saving sounds to {SOUNDS_FILE}")
        pickle.dump((BASIC_SOUNDS, ORGAN_SOUNDS), f)
print("Sounds loaded!")


class SoundSeq():
    def __init__(self, sounds: list[Sound] = None, fs=8000, debug=False):
        if debug:
            print("Creating SoundSeq using", (sounds))
        self.sounds: list[Sound] = []
        self.audio = None
        self.fs = fs
        sounds = list(sounds)
        for s in sounds:
            if isinstance(s, Sound):
                self.sounds.append(s)
        self.change_duration()
        if debug:
            print("Creating SoundSeq using", (sounds))

    def append(self, other):  # very slow operation
        if isinstance(other, Sound) and other.fs == self.fs:
            self.sounds.append(other)
            self.change_duration()

    def change_duration(self):
        if self.is_playing():
            self.stop()
        seconds = 0
        size = 0
        for s in self.sounds:
            if isinstance(s, Sound):
                seconds += s.seconds
                size += s.size

        self.audio = bytearray(size * 2)
        self.size = size
        self.seconds = seconds
        self.update_audio()

    def update_audio(self):
        new_audio = b''.join([s.audio for s in self.sounds])
        for i, a in enumerate(new_audio):
            self.audio[i] = a
        return self.audio

    def play(self):
        if self.is_playing():
            self.stop()
        self.player = sa.play_buffer(self.audio, 1, 2, self.fs)

    def stop(self):
        if getattr(self, 'player', None) is not None:
            self.player.stop()
            self.player = None

    def is_playing(self):
        if getattr(self, 'player', None) is not None:
            return self.player.is_playing()
        return False

    def wait_done(self):
        if getattr(self, 'player', None) is not None:
            self.player.wait_done()
            self.player = None

    def __len__(self):
        return self.size

    def __add__(self, other):
        if isinstance(other, Sound):
            return SoundSeq(self.sounds + other)
        elif isinstance(other, SoundSeq):
            return SoundSeq(self.sounds + other.sounds)
        raise TypeError("Added value is of an invalid type. Must be Sound or SoundSeq.")

    def __mul__(self, factor):
        if type(factor) == int:
            return SoundSeq(self.sounds * abs(factor))

    def __repr__(self):
        return '[ ' + ',\n'.join(map(str, self.sounds)) + ' ]'


def sound_example():
    "Example of using the sound module."
    play_freq(440)
    play_note("Bb4")
    play_many_notes([("A4", 0.5, 0.2), ("E4", 0.5, 0.2), ("C4", 0.5, 0.2), ("F4", 0.5, 0.2)])
    play_note("A4", seconds=3, bg_play=True)  # play a note in the background
    input("Playing sound in background. Press Enter to Continue.")


def sound_example_cycle_instruments():
    for note_name in NOTE_NAMES[80:100]:
        print(note_name)
        play_note('D4', seconds=0.1, instrument=note_name, instrument_strength=10)


def sound_example_cycle_pitches():
    for i, note_name in enumerate(NOTE_NAMES[70:90]):
        print(i, note_name)
        (play_note(note_name, seconds=0.1, vol_factor=0.5, instrument='A4', instrument_strength=10))


def sound_example_cycle_strength():
    for i in range(0, 200, 10):
        print(i)
        play_note('A4', seconds=0.1, vol_factor=0.5, instrument='A4', instrument_strength=i)


def sound_example_Sound_Object():
    s = Sound(seconds=10, vol_factor=0.2, instrument=None)
    s.play()
    input("Press Enter to stop")
    s.stop()


def sound_example_SoundSeqObject():
    s = []
    s.append(Sound('D3', seconds=1, vol_factor=0.2, instrument=None))
    s.append(Sound('A3', seconds=1, vol_factor=0.2, instrument=None))
    s.append(Sound('E3', seconds=1, vol_factor=0.2, instrument=None))
    seq = SoundSeq(s)
    seq.play()
    input("Press Enter to cutoff sound and continue...")
    seq.append(s[0])
    input("Press Enter to cutoff sound and continue...")
    seq.play()
    input("Press Enter to cutoff sound and continue...")
    seq.stop()


def sound_example_for_basic_and_organ_sounds():
    "Example to show the use of BASIC_SOUNDS and ORGAN_SOUNDS."
    for d in [BASIC_SOUNDS, ORGAN_SOUNDS]:
        for note, sound in d.items():
            if int(note[-1]) in range(3, 7):  # avoid very low/high pitch notes
                try:
                    sound.play()
                    print(f"Played {note}")
                except Exception as e:  # sometimes this fails with SimpleaudioError, especially for lower pitch notes
                    print(f"Failed to play {note} with error {e}")
                sleep(0.3)


if __name__ == "__main__":
    sound_example_SoundSeqObject()
    sound_example_Sound_Object()
    print("Playing Basic Sounds...")
    sound_example()
    print("New Instruments:")
    sound_example_cycle_instruments()
    print("Apply Instrument Strength:")
    sound_example_cycle_strength()
    print("Different pitches using an instrument:")
    sound_example_cycle_pitches()
    sound_example_for_basic_and_organ_sounds()
