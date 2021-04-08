import RPi.GPIO as GPIO
import picamera

from config import config
from datetime import datetime
from subprocess import call, DEVNULL, check_output, STDOUT
from pathlib import Path
import threading
import shutil
import time
import sys
import re


class GGCam():

    try:
        duration = int(config['duration'])
        mount_folder = Path(config['mount_folder'])
        h264_files = [Path(config['h264_file']), Path(config['h264_file_2'])]
        output_folder = Path(config['output_folder'])
        partition_id = config['partition_id']
    except Exception as e:
        print(f'==> something wrong with config.py. \n\terror: {e}')
        sys.exit(1)

    self.temp_file = self.mount_folder.joinpath('temp.h264')
    self.h264_index = 0 

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
        
    def jumping_h264_file_index()
        if self.h264_index + 1 < len(self.h264_files):
            self.h264_index += 1
        else:
            self.h264_index = 0

    def record(self):
        with picamera.PiCamera() as cam:
            cam.resolution=(1920,1080)
            cam.annotate_background = picamera.Color('black')
            cam.framerate = self.fps
            cam.start_preview()
            cam.start_recording(str(self.h264_files[self.h264_index]))
        
            start = datetime.now()
            print(f'\n==> Recording clip start at {start.strftime("%Y-%m-%d %H:%M:%S")}')
            print(f'==> Duration : {self.duration} secs')

            while True:
                if GPIO.input(3):
                    print('\n==> Recording stopped.')
                    return

                if (datetime.now() - start).seconds >= self.duration:
                    cam.stop_recording()
                    # record with another file for no delay
                    self.jumping_h264_file_index()
                    cam.start_recording(str(self.h264_files[self.h264_index])
                    
                    #  TODO here
                    shutil.copy(self.jumping_h264_file, self.temp_file)

                    th_1 = threading.Thread(target=self.convert_video, args=())
                    th_1.start()

                    cam.start_recording(str(self.h264_file))
                    start = datetime.now()
                    print(f'\n==> Recording clip start at {start.strftime("%Y-%m-%d %H:%M:%S")}')
                    print(f'==> Duration : {self.duration} secs')

                cam.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cam.wait_recording(0.1)
                time.sleep(1)
    
    def convert_video(self):
        print('\n==> Start converting video ...')
        # self.temp_file = self.mount_folder.joinpath('temp.h264')
        # shutil.copy(self.h264_file, self.temp_file)

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output = self.output_folder.joinpath(f'{timestamp}.mp4')

        exited_code = call(["MP4Box", "-add", f'{self.temp_file}:fps=30', output], stdout=DEVNULL)
        if exited_code:
            print('==> Converting failed. exited')
            sys.exit(1)
        else:
            print('==> Converting done. Mp4 file saved to {output}.')
        self.temp_file.unlink()
        

    def run(self):
        # print('\n==> Ready for recording ...')
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(3, GPIO.IN)
        
        msg_showed = True
        while True:
            if not GPIO.input(3):
                self.record()
                self.convert_video()
                msg_showed = not msg_showed
            else:
                if msg_showed:
                    print('\n==> Standby for recording ...')
                    msg_showed = not msg_showed
            time.sleep(1)


if __name__ == '__main__':
    a = GGCam()
    a.convert_video()