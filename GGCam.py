from datetime import datetime
from subprocess import call, DEVNULL, check_output
import picamera
import time
from pathlib import Path
import sys


is_usb_mouned = call('mount -l | grep sda1', shell=True, stdout=DEVNULL, stderr=DEVNULL)
if is_usb_mouned:
    print('\n==> usb drive not found. Trying to mount...')
    mount_result = call(['/home/pi/PiGGCam/mount_usb.sh'], stdout=DEVNULL, stderr=DEVNULL)
    if mount_result != 0:
        print('==> Can\'t mount usb. Exited.\n')
        sys.exit(1)
    else:
        print('==> usb drive mounted.\n')


usb_video_folder = Path('/mnt/usb/videos')
if not usb_video_folder.exists():
    print('\n==> Create folder: "videos" on usb drive.')
    usb_video_folder.mkdir()

temp_h264_file = Path('/home/pi/video.h264')

duration = 60 
 
print('\n==> Start recording ...')
with picamera.PiCamera() as cam:
    cam.resolution=(1920,1080)
    cam.annotate_background = picamera.Color('black')
    cam.start_preview()
    cam.start_recording(str(temp_h264_file))
    
    start = datetime.now()
    count = 0
    while (datetime.now() - start).seconds < duration:
        cam.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cam.wait_recording(0.1)
        print(count)
        count +=1
        time.sleep(1)

print('==> Done recording\n')


timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

print('==> Processing video: ')

output = usb_video_folder.joinpath(f'{timestamp}.mp4')
print(f'==> Saving to {output}')

call(["MP4Box", "-add", temp_h264_file, output], stdout=DEVNULL, stderr=DEVNULL)
print('\n==> Done. mp4 file saved.\n')

