import time
from gpiozero import Button, LED

led_green = LED(26)
led_red = LED(19)
button = Button(23)

while 1:
    if button.is_pressed:
        print('pressed')
        target = led_green
        target.on()
        time.sleep(0.1)
        target.off()
        time.sleep(0.1)

    else:
        print('not pressed')
        target = led_red
        target.on()
        time.sleep(0.1)
        target.off()
        time.sleep(0.1)

