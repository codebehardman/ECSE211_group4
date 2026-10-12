from utils.brick import Motor
import time

m = Motor("A")

m.set_power(50); time.sleep(2); m.set_power(0)
