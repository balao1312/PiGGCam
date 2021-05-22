from gpiozero import MotionSensor
import gpiozero
import time
from datetime import datetime

pir = MotionSensor(21)
led = gpiozero.LED(4)
while 1:
    if pir.motion_detected:
        print(f'Motion detected!')
        with open('motion.log', 'a') as f:
            f.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        led.on()
    else:
        print(f'Nothing')
        led.off()
    
    time.sleep(1)
