import time
from gpiozero import Button, LED

button = Button(19)

while 1:
    if button.is_pressed:
        print('pressed')
    else:
        print('not pressed')
    time.sleep(1)
