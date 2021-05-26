import time
from gpiozero import Button, LED

led_green = LED(26)
led_red = LED(19)

while 1:
    led_green.on()
    time.sleep(0.5)
    led_green.off()
    time.sleep(0.5)

    led_red.on()
    time.sleep(0.5)
    led_red.off()
    time.sleep(0.5)
