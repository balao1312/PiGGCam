from gpiozero import PWMLED
from time import sleep

led = PWMLED(4)

while True:
    # led.value = 0  # off
    # sleep(1)
    # led.value = 0.5  # half brightness
    # sleep(1)
    # led.value = 1  # full brightness
    # sleep(1)

    for brightness in range(0, 11):
        print(f'now {brightness / 10}')
        led.value = brightness / 10
        sleep(0.2)