# import RPi.GPIO as GPIO
# import picamera

from config import config
from logging_custom_time import logger
from datetime import datetime
from subprocess import call, DEVNULL, check_output, STDOUT
from pathlib import Path
from copy import deepcopy, copy
import threading
import logging
import time
import sys
import re


class GGCam():

    clip_count = 0
    clip_start_time = None
    timestamp_filename = None
    show_msg = True
    any_error = False

    try:
        duration = config['duration']
        mount_folder = Path(config['mount_folder'])
        output_folder = Path(config['output_folder'])
        partition_id = config['partition_id']
        fps = config['fps']
        resolution = config['resolution']
    except Exception as e:
        # print(f'==> something wrong with config.py. \n\terror: {e}')
        # sys.exit(1)
        any_error = True
        error_msg = f'==> something wrong with config.py. \n\terror: {e}'
        # make a reset script for user
    
    h264_files = {
        'recording': mount_folder.joinpath('temp.h264'),
        'done': mount_folder.joinpath('temp_2.h264')
    }

    # usb_status_checktime = None

    def __init__(self):
        self.my_logger = logger()
        self.my_logger.info('PiGGCam starting ...', extra={'timestamp': time.time()})
        self.usb_status = self.reset_usb_status()
        self.last_usb_status = deepcopy(self.usb_status)
        log_folder = Path('./logs')
        if not log_folder.exists():
            log_folder.mkdir()

    def GGCam_init(self):
        self.usb_status_checktime = time.time()
        self.check_usb_partition_table()
        if self.usb_status['partition_table']['status'] is None:
            self.reset_usb_status()
            return

        self.check_mount_folder()
        self.check_usb_mount()
        self.try_mount_succeeded_usb()
        self.check_output_folder()

    def reset_usb_status(self):
        return {
            'partition_table': {
                'status': None,
                'msg': '',
            },
            'mount_folder_exists': {
                'status': False,
                'msg': '',
            },
            'usb_drive_mounted': {
                'status': False,
                'msg': '',
            },
            'try_mount_succeeded': {
                'status': None,
                'msg': '',
            },
            'output_folder_exists': {
                'status': False,
                'msg': '',
            }
        }

# ------------------------------------------------------------------------------------------
    # check if there is any USB drive and get USB drive partition table (gpt or dos)
    def check_usb_partition_table(self):
        cmd = f'sudo /usr/sbin/fdisk -l | grep -n4 {self.partition_id}'
        try:
            output = check_output(
                [cmd], timeout=3, stderr=STDOUT, shell=True).decode('utf8')
            target = re.compile(r'Disklabel type: (.*)')
            result = target.search(output)
            self.usb_status['partition_table']['msg'] = f'USB drive found. Partition table is : {result.group(1)}'
            self.usb_status['partition_table']['status'] = result.group(1)
        except Exception as e:
            self.usb_status['partition_table']['status'] = None
            self.usb_status['partition_table']['msg'] = f'No USB drive found. Please insert a USB drive.'

    def check_mount_folder(self):
        exited_code = call(f'ls {self.mount_folder}',
                           shell=True, stdout=DEVNULL)
        self.usb_status['mount_folder_exists']['status'] = True
        if not exited_code:
            self.usb_status['mount_folder_exists']['msg'] = f'{self.mount_folder} already existed.'
        else:
            call(f'sudo mkdir {self.mount_folder}', shell=True)
            self.usb_status['mount_folder_exists']['msg'] = f'{self.mount_folder} created.'

    def check_usb_mount(self):
        exited_code = call(
            f'mount -l | grep {self.partition_id}', shell=True, stdout=DEVNULL)
        if not exited_code:
            self.usb_status['usb_drive_mounted']['status'] = True
            self.usb_status['usb_drive_mounted']['msg'] = 'USB drive already mounted.'
        else:
            self.usb_status['usb_drive_mounted']['status'] = False
            self.usb_status['usb_drive_mounted']['msg'] = 'USB drive is not mounted.'

    def try_mount_succeeded_usb(self):
        exited_code = call('sudo mount -a', shell=True, stdout=DEVNULL)
        if not exited_code:
            self.usb_status['try_mount_succeeded']['status'] = True
            self.usb_status['try_mount_succeeded']['msg'] = 'USB drive mounted successfully'
        else:
            self.usb_status['try_mount_succeeded']['status'] = False
            self.usb_status['try_mount_succeeded']['msg'] = 'Can\'t mount usb drive, maybe some problem with /etc/fstab.'

    def check_output_folder(self):
        if not self.output_folder.exists():
            self.my_logger.error(f'{self.output_folder} doesn\'t exists.')
            try:
                self.output_folder.mkdir()
            except PermissionError:
                self.usb_status['output_folder_exists']['msg'] = f'Can\'t create {self.output_folder} folder.'
                return
            self.usb_status['output_folder_exists']['msg'] = f'{self.output_folder} created for output.'
        else:
            self.usb_status['output_folder_exists']['msg'] = f'{self.output_folder} already exists.'
        self.usb_status['output_folder_exists']['status'] = True
        
# ----------------------------------------------------------------------------------------------

    def swap_h264_set(self):
        self.h264_files['recording'], self.h264_files['done'] = self.h264_files['done'], self.h264_files['recording']

    def record(self):
        def start_recording_session():
            self.clip_count += 1
            self.clip_start_time = datetime.now()
            self.timestamp_filename = self.clip_start_time.strftime(
                '%Y%m%d_%H-%M-%S')
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
                    cam.stop_recording()
                    th_2 = threading.Thread(target=self.convert_video, args=(
                        self.h264_files['recording'], self.timestamp_filename, self.clip_count))
                    th_2.start()
                    th_2.join()
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
            ["MP4Box", "-add", f'{file}:fps={self.fps}', output], stdout=DEVNULL, stderr=DEVNULL)
        if exited_code:
            print(f'==> Clip {count} convert failed.')
            # sys.exit(1)
            self.any_error = True
            self.error_msg = f'==> Clip {count} convert failed.'
        else:
            print(
                f'\n==> Clip {count} convert done. Mp4 file saved to {output}.')
            file.unlink()

    def run(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(3, GPIO.IN)

        show_msg = True
        while True:
            if not GPIO.input(3) and not self.any_error:
                self.record()
                show_msg = not show_msg
            else:
                if show_msg:
                    if not self.any_error:
                        print('\n==> Standby for recording ...')
                    else:
                        print(f'\n==> Error: {self.error_msg}')
                    show_msg = not show_msg
            time.sleep(1)

    def log_usb_status(self):
        
        # print([(key, value) for key in self.usb_status.keys() if key in self.usb_status_changed_list for value in self.usb_status.values() if key in self.usb_status_changed_list])
        
        for key, values in self.usb_status.items():
            if not key in self.usb_status_changed_list:
                continue

            if values['status']:
                self.my_logger.info(values['msg'], extra={'timestamp': self.usb_status_checktime})
            else:
                self.my_logger.error(values['msg'])

    @property
    def usb_status_changed(self):
        return not self.usb_status == self.last_usb_status
        
    def test_record(self):
        while 1:
            if open('gpio', 'r').read():
                print('\n==> Recording stopped.')
                return
            print('recording...')
            time.sleep(1)

    def test_run(self):
        
        while True:
            # GPIO = str(open('gpio', 'r').read())

            self.GGCam_init()

            # check any diff, and change show_msg
            # print(self.usb_status_changed)
            if self.usb_status_changed:
                self.usb_status_changed_list = []
                for key, values in self.usb_status.items():
                    # print(values, self.last_usb_status[key])
                    # print(values == self.last_usb_status[key])
                    if values != self.last_usb_status[key]:
                        self.usb_status_changed_list.append(key)
                # print(self.usb_status_changed_list)
                self.show_msg = True
            
            self.last_usb_status = deepcopy(self.usb_status)


            if self.show_msg:
                self.log_usb_status()
                self.show_msg = False


            # cant record due to some errors
            # if self.any_error and show_msg:
            #     print(f'\n==> Error: {self.error_msg}')
            #     show_msg = not show_msg

            # # no error ready to record
            # else:
            #     if not GPIO:
            #         self.test_record()
            #         show_msg = not show_msg
            #     if show_msg:
            #         if not self.any_error:
            #             print('\n==> Standby for recording ...')
            #         show_msg = not show_msg
            time.sleep(1)

if __name__ == '__main__':
    a = GGCam()
    a.test_run()
