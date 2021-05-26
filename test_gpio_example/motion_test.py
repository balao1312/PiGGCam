from gpiozero import MotionSensor
import gpiozero
import time

pir = MotionSensor(21)

while 1:
    if pir.motion_detected:
        print(f'Motion detected!')
    else:
        print(f'Nothing')
    
    time.sleep(1)
