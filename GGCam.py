from datetime import datetime
from subprocess import call, DEVNULL, check_output
import picamera
import time
from pathlib import Path
import sys
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(3, GPIO.IN)

is_usb_mouned = call('mount -l | grep sda1', shell=True, stdout=DEVNULL, stderr=DEVNULL)
if is_usb_mouned:
    print('\n==> usb drive not found. Trying to mount...')
    mount_result = call(['./mount_usb.sh'], stdout=DEVNULL, stderr=DEVNULL)
    if mount_result != 0:
        print('==> Can\'t mount usb. Exited.\n')
        sys.exit(1)
    else:
        print('==> usb drive mounted.')


usb_video_folder = Path('/mnt/usb/videos')
if not usb_video_folder.exists():
    print('\n==> Create folder: "videos" on usb drive.')
    usb_video_folder.mkdir()

temp_h264_file = Path('/home/pi/video.h264')

# duration = 10000000
 
print('\n==> Start recording ...')

def processing_video():
    print('==> Processing video: ')
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    output = usb_video_folder.joinpath(f'{timestamp}.mp4')

    print(f'==> Saving to {output}')
    call(["MP4Box", "-add", f'{temp_h264_file}:fps=30', output])#, stdout=DEVNULL, stderr=DEVNULL)
    print('\n==> Done. mp4 file saved.\n')
    temp_h264_file.unlink()

def recording():
    with picamera.PiCamera() as cam:
        cam.resolution=(1920,1080)
        cam.annotate_background = picamera.Color('black')
        cam.framerate = 30
        cam.start_preview()
        cam.start_recording(str(temp_h264_file))
    
        start = datetime.now()
        count = 0
        while True: #(datetime.now() - start).seconds < duration:
            if (datetime.now() - start).seconds > 10:
                cam.stop_preview()
            cam.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cam.wait_recording(0.1)
            print(count)
            count +=1
            if GPIO.input(3):
                return
            time.sleep(1)

while True:
    if not GPIO.input(3):
        recording()
        processing_video()
        print('==> Done recording\n')

    time.sleep(1)


