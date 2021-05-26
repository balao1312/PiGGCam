import RPi.GPIO as GPIO
import time
  
GPIO.setmode(GPIO.BCM)
  
# The input pin of the Sensor will be declared. Additional to that the pullup resistor will be activated.
GPIO_PIN = 19
GPIO.setup(GPIO_PIN, GPIO.IN, pull_up_down = GPIO.PUD_UP)
  
print("Sensor-Test [press ctrl+c to end it]")
  
count = 0
# This output function will be started at signal detection
def outFunction(null):
        global count
        count += 1
        print(f"Signal detected, count={count}")
  
# At the moment of detecting a Signal ( falling signal edge ) the output function will be activated.
GPIO.add_event_detect(GPIO_PIN, GPIO.FALLING, callback=outFunction, bouncetime=100) 
  
# main program loop
try:
        while True:
                time.sleep(1)
  
# Scavenging work after the end of the program
except KeyboardInterrupt:
        GPIO.cleanup()