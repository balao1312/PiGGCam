import time
from gpiozero import Button, LED

led = LED(24)
led_red = LED(4)
button = Button(23)

while 1:
    if button.is_pressed:
        print('pressed')
        led.on()
        led_red.on()
        time.sleep(1)
        led.off()
        led_red.off()
    else:
        print('not pressed')
    time.sleep(1)
