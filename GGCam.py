import RPi.GPIO as GPIO
import picamera

from config import config
from datetime import datetime
from subprocess import call, DEVNULL, check_output, STDOUT
from pathlib import Path
import threading
import time
import sys
import re


class GGCam():
    try:
        duration = config['duration']
        mount_folder = Path(config['mount_folder'])
        output_folder = Path(config['output_folder'])
        partition_id = config['partition_id']
        fps = config['fps']
        resolution = config['resolution']
    except Exception as e:
        print(f'==> something wrong with config.py. \n\terror: {e}')
        sys.exit(1)

    h264_files = {
        'recording': mount_folder.joinpath('temp.h264'),
        'done': mount_folder.joinpath('temp_2.h264')
    }

    clip_count = 0
    clip_start_time = None
    timestamp_filename = None

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
            output = check_output(
                [cmd], timeout=3, stderr=STDOUT, shell=True).decode('utf8')
            target = re.compile(r'Disklabel type: (.*)')
            result = target.search(output)
            return result.group(1)
        except:
            return None

    def check_usb_mount(self):
        exited_code = call(
            f'mount -l | grep {self.partition_id}', shell=True, stdout=DEVNULL)
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
        exited_code = call(f'ls {self.mount_folder}',
                           shell=True, stdout=DEVNULL)
        if exited_code:
            call(f'sudo mkdir {self.mount_folder}', shell=True)
            print(f'==> {self.mount_folder} created.')

    def check_output_folder(self):
        if not self.output_folder.exists():
            self.output_folder.mkdir()
            print(f'==> {self.output_folder} created for output')

    def swap_h264_set(self):
        self.h264_files['recording'], self.h264_files['done'] = self.h264_files['done'], self.h264_files['recording']

    def record(self):
        def start_recording_session():
            self.clip_count += 1
            self.clip_start_time = datetime.now()
            self.timestamp_filename = self.clip_start_time.strftime(
                '%Y-%m-%d_%H-%M-%S')
            cam.start_recording(str(self.h264_files['recording']))
            print(
                f'\n==> Recording clip {self.clip_count} , start at {self.clip_start_time.strftime("%Y-%m-%d %H:%M:%S")}')
            print(f'==> Duration : {self.duration} secs')

        with picamera.PiCamera() as cam:
            cam.resolution = self.resolution
            cam.annotate_background = picamera.Color('black')
            cam.framerate = self.fps
            cam.start_preview()

            start_recording_session()

            while True:
                if GPIO.input(3):
                    print('\n==> Recording stopped.')
                    th_2 = threading.Thread(target=self.convert_video, args=(
                        self.h264_files['recording'], self.timestamp_filename, self.clip_count))
                    th_2.start()
                    return

                if (datetime.now() - self.clip_start_time).seconds >= self.duration:
                    cam.stop_recording()

                    # swap recording file and done recored file refference
                    self.swap_h264_set()

                    # start another thread to convert done recorded file
                    th_1 = threading.Thread(target=self.convert_video, args=(
                        self.h264_files['done'], self.timestamp_filename, self.clip_count))
                    th_1.start()

                    # record with another file for no delay
                    start_recording_session()

                cam.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cam.wait_recording(0.1)
                time.sleep(0.9)

    def convert_video(self, file, timestamp, count):
        output = self.output_folder.joinpath(f'{timestamp}.mp4')
        exited_code = call(
            ["MP4Box", "-add", f'{file}:fps={self.fps}', output], stdout=DEVNULL)
        if exited_code:
            print(f'==> Clip {count} convert failed. exited')
            sys.exit(1)
        else:
            print(
                f'==> Clip {count} convert done. Mp4 file saved to {output}.')
            file.unlink()

    def run(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(3, GPIO.IN)

        show_msg = True
        while True:
            if not GPIO.input(3):
                self.record()
                show_msg = not show_msg
            else:
                if show_msg:
                    print('\n==> Standby for recording ...')
                    show_msg = not show_msg
            time.sleep(1)


if __name__ == '__main__':
    pass
