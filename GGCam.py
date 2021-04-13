import RPi.GPIO as GPIO
import picamera

from config import config
from datetime import datetime
from subprocess import call, DEVNULL, check_output, STDOUT
from pathlib import Path
from copy import deepcopy
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
    usb_status_changed_list = []
    ready_for_recording = False
    
    def __init__(self):
        logging_format = '[%(asctime)s] %(levelname)s: %(message)s'
        logging_datefmt = '%Y-%m-%d %H:%M:%S'
        logging.basicConfig(level=logging.INFO, format=logging_format, datefmt=logging_datefmt,
            handlers=[logging.FileHandler(f'./logs/{datetime.now().strftime("%Y-%m-%d")}.log'), logging.StreamHandler()])

        self.load_config_from_file()
        self.h264_files = {
            'recording': self.mount_folder.joinpath('temp.h264'),
            'done': self.mount_folder.joinpath('temp_2.h264')
        }

        self.usb_status = self.usb_status_initiated
        self.last_usb_status = deepcopy(self.usb_status)

        self.log_folder = Path('./logs')
        if not self.log_folder.exists():
            self.log_folder.mkdir()
    
    def load_config_from_file(self):
        try:
            self.duration = config['duration']
            self.mount_folder = Path(config['mount_folder'])
            self.output_folder = Path(config['output_folder'])
            self.partition_id = config['partition_id']
            self.fps = config['fps']
            self.resolution = config['resolution']
        except Exception as e:
            # any_error = True
            logging.error(f'something wrong with config.py. {e.__class__}: {e}')
            logging.info('Exited.')
            # make a reset script for user
            sys.exit(1)

    def GGCam_init(self):
        self.check_usb_partition_table()
        if self.usb_status['partition_table']['status'] is None:
            self.usb_status = self.usb_status_initiated
            self.usb_status['partition_table']['msg'] = 'No USB drive found. Please insert a USB drive.'
            return
        
        if not self.usb_status['usb_drive_mounted']['status']:
            self.adapt_fstab(self.usb_status['partition_table']['status'])

        self.check_mount_folder()
        self.check_usb_mount()
        self.try_mount_succeeded_usb()
        self.check_output_folder()

    @property
    def usb_status_initiated(self):
        return {
            'partition_table': {
                'status': None,
                'msg': '',
            },
            'mount_folder_exists': {
                'status': False,
                'msg': '',
            },'try_adapt_fstab': {
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

# ---------------------------------------------------------------------------------------
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
            # self.adapt_fstab(result.group(1))
        except Exception as e:
            self.usb_status['partition_table']['status'] = None
            self.usb_status['partition_table']['msg'] = f'No USB drive found. Please insert a USB drive.'

    def adapt_fstab(self, partition_table):
        if partition_table == 'dos':
            cmd = 'sudo cp -f ./fstab_dos /etc/fstab'
        elif partition_table == 'gpt':
            cmd = 'sudo cp -f ./fstab_gpt /etc/fstab'
        exited_code = call(cmd, shell=True)
        if not exited_code:
            self.usb_status['try_adapt_fstab']['status'] = True
            self.usb_status['try_adapt_fstab']['msg'] = f'modify /etc/fstab for {partition_table}'
        else:
            self.usb_status['try_adapt_fstab']['msg'] = f'modify /etc/fstab failed.'

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
            self.usb_status['usb_drive_mounted']['msg'] = 'USB drive is mounted.'
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
            try:
                self.output_folder.mkdir()
            except PermissionError:
                self.usb_status['output_folder_exists']['msg'] = f'Can\'t create {self.output_folder} folder.'
                return
            self.usb_status['output_folder_exists']['msg'] = f'{self.output_folder} created for output.'
        self.usb_status['output_folder_exists']['status'] = True
        
# ---------------------------------------------------------------------------------------

    def swap_h264_set(self):
        self.h264_files['recording'], self.h264_files['done'] = self.h264_files['done'], self.h264_files['recording']

    def record(self):
        def start_recording_session():
            self.clip_count += 1
            self.clip_start_time = datetime.now()
            self.timestamp_filename = self.clip_start_time.strftime(
                '%Y%m%d_%H-%M-%S')
            cam.start_recording(str(self.h264_files['recording']))
            logging.info(
                f'Start recording clip {self.clip_count} at {self.clip_start_time.strftime("%Y-%m-%d %H:%M:%S")}, duration: {self.duration} secs')

        with picamera.PiCamera() as cam:
            cam.resolution = self.resolution
            cam.annotate_background = picamera.Color('black')
            cam.framerate = self.fps
            cam.start_preview()

            start_recording_session()

            while True:
                if GPIO.input(3):
                    logging.info('Button pressed for stop recording.')
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
            logging.error(f'Clip {count} convert failed.')
            # sys.exit(1)
        else:
            logging.info(
                f'Clip {count} convert done. Mp4 file saved to {output.name}.')
            file.unlink()

    def check_ready_for_recording(self):
        for key, values in self.usb_status.items():
            if not values['status']:
                self.ready_for_recording = False
                return
            self.ready_for_recording = True

    def run(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(3, GPIO.IN)

        logging.info('PiGGCam starting ...')

        while True:
            self.GGCam_init()

            # check any diff
            if self.usb_status_changed:
                self.usb_status_changed_list = []
                for key, values in self.usb_status.items():
                    if values != self.last_usb_status[key]:
                        self.usb_status_changed_list.append(key)

                # check if everything is ready
                self.check_ready_for_recording()

                self.log_usb_status()
                self.show_msg = True

            self.last_usb_status = deepcopy(self.usb_status)

            if not GPIO.input(3) and self.ready_for_recording:
                self.record()
            else:
                if self.show_msg and self.ready_for_recording:
                    logging.info('Standby for recording ...')
                    self.show_msg = False

            time.sleep(1)

    def log_usb_status(self):
        for key, values in self.usb_status.items():
            if not key in self.usb_status_changed_list:
                continue
            if not values['msg']:
                continue

            if values['status']:
                logging.info(values['msg'])
            else:
                logging.error(values['msg'])

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
        logging.info('PiGGCam starting ...')

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
    a.run()
