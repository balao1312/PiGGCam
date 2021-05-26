import time
from gpiozero import Button, LED

led = LED(24)

while 1:
    led.on()
    time.sleep(1)
    led.off()
    time.sleep(1)
