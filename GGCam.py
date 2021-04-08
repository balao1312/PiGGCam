import RPi.GPIO as GPIO
import picamera
from config import config
from datetime import datetime
from subprocess import call, DEVNULL, check_output, STDOUT
import time
from pathlib import Path
import sys
import re


class GGCam():

    try:
        interval = int(config['interval'])
        mount_folder = Path(config['mount_folder'])
        temp_h264_file = Path(config['temp_h264_file'])
        output_folder = Path(config['output_folder'])
        partition_id = config['partition_id']
    except Exception as e:
        print(f'==> something wrong with config.py. \n\terror: {e}')


    def __init__(self):
        # check if there is any USB drive and get USB drive partition table (gpt or dos)
        usb_partition_table = self.check_usb_partition_table()
        if usb_partition_table:
            print(f'==> USB drive partition table is : {usb_partition_table}')
        else:
            print('==> no USB drive found. exited.')
            sys.exit(1)

        self.check_mount_folder()

        if self.check_usb_mount():
            print('==> USB drive already mounted.')
        else:
            print('==> USB drive is not mounted.')
            self.try_mount_usb()
        
        self.check_output_folder()

    def check_usb_partition_table(self):
        cmd = f'sudo /usr/sbin/fdisk -l | grep -n4 {self.partition_id}'
        try:
            output = check_output([cmd], timeout=3, stderr=STDOUT, shell=True).decode('utf8')
            target = re.compile(r'Disklabel type: (.*)')
            result = target.search(output)
            return result.group(1)
        except:
            return None
    
    def check_usb_mount(self):
        exited_code = call(f'mount -l | grep {self.partition_id}', shell=True, stdout=DEVNULL)
        return False if exited_code else True

    def try_mount_usb(self):
        print('==> trying to mount USB drive ...')
        exited_code = call('sudo mount -a', shell=True)
        if exited_code:
            print('==> USB drive mount failed.')
            sys.exit(1)
        else:
            print('==> USB drive mounted successfully')
            
    def check_mount_folder(self):
        exited_code = call(f'ls {self.mount_folder}', shell=True, stdout=DEVNULL)
        # print(exited_code)
        if exited_code:
            call(f'sudo mkdir {self.mount_folder}', shell=True)
            print(f'==> {self.mount_folder} created.')

    def check_output_folder(self):
        if not self.output_folder.exists():
            self.output_folder.mkdir()
            print(f'==> {self.output_folder} created for output')
        
    def record(self):
        with picamera.PiCamera() as cam:
            cam.resolution=(1920,1080)
            cam.annotate_background = picamera.Color('black')
            cam.framerate = 30
            cam.start_preview()
            cam.start_recording(str(self.temp_h264_file))
        
            start = datetime.now()
            while True:
                print(f'==> Recording clip start at {start.strftime('%Y-%m-%d %H:%M:%S')}')
                # if (datetime.now() - start).seconds > 10:
                    # cam.stop_preview()
                cam.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cam.wait_recording(0.1)
                if GPIO.input(3):
                    return
                time.sleep(1)
    
    def convert_video(self):
        print('==> Start converting video ...')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output = self.output_folder.joinpath(f'{timestamp}.mp4')
        print(f'==> Saving to {output}')

        call(["MP4Box", "-add", f'{self.temp_h264_file}:fps=30', output])
        print('==> Converting done. Mp4 file saved.\n\n==> Ready for recording ...')
        self.temp_h264_file.unlink()

    def run(self):
        print('\n==> Ready for recording ...')
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(3, GPIO.IN)
        
        while True:
            if not GPIO.input(3):
                self.record()
                self.convert_video()
            time.sleep(1)
