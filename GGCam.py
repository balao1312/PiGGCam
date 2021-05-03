import gpiozero
import picamera

from config import config
from datetime import datetime
from subprocess import DEVNULL, check_output, STDOUT, run
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
    converting_video = 0
    button = gpiozero.Button(3)
    mount_folder = '/mnt/usb'
    
    def __init__(self):
        logging_format = '[%(asctime)s] %(levelname)s: %(message)s'
        logging_datefmt = '%Y-%m-%d %H:%M:%S'
        logging.basicConfig(level=logging.DEBUG, format=logging_format, datefmt=logging_datefmt,
            handlers=[logging.FileHandler(f'./logs/{datetime.now().strftime("%Y-%m-%d")}.log'), logging.StreamHandler()])

        self.load_config_from_file()

        self.temp_h264_folder = Path('./temp')
        if not self.temp_h264_folder.exists():
            self.temp_h264_folder.mkdir()

        self.h264_files = {
            'recording': Path('./temp/temp1.h264'),
            'done': Path('./temp/temp2.h264'),
        }

        self.usb_status = self.usb_status_initiated
        self.last_usb_status = deepcopy(self.usb_status)

        self.log_folder = Path('./logs')
        if not self.log_folder.exists():
            self.log_folder.mkdir()
    
    def load_config_from_file(self):
        try:
            self.duration = config['duration']
            self.output_folder = Path('./videos') # Path(config['output_folder'])
            self.fps = config['fps']
            self.resolution = config['resolution']
        except Exception as e:
            logging.error(f'something wrong with config.py. {e.__class__}: {e}')
            logging.info('Exited.')
            # make a reset script for user
            sys.exit(1)

    def GGCam_init(self):
        self.check_usb_partition_id()

        if self.usb_status['partition_id']['status'] is None:
            self.log_usb_status()
            self.usb_status = self.usb_status_initiated
            return
        
        if not self.usb_status['usb_drive_mounted']['status']:
            self.adapt_fstab(self.usb_status['partition_id']['status'])

        self.check_mount_folder()
        self.check_usb_mount()
        self.check_output_folder()
        
        self.log_usb_status()

    @property
    def usb_status_initiated(self):
        return {
            'partition_id': {
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
            'try_mount_usb': {
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
    def check_usb_partition_id(self):
        cmd = f"sudo /usr/sbin/fdisk -l | grep -P 'sd[abc]\d' | grep -P '\d*(.\d)*G'"
        try:
            output = check_output(
                [cmd], timeout=3, stderr=STDOUT, shell=True).decode('utf8').strip()
            target = re.compile(r'(sd[abc]\d{1})')
            result = target.search(output)
            self.usb_status['partition_id']['msg'] = f'USB drive found. Partition id is : {result.group(1)}'
            self.usb_status['partition_id']['status'] = result.group(1)
            self.adapt_fstab(result.group(1).strip())
        except Exception as e:
            self.usb_status['partition_id']['status'] = None
            self.usb_status['partition_id']['msg'] = f'No USB drive found. Please insert a USB drive.'
            logging.debug(f'{e.__class__}: {e}')

    def adapt_fstab(self, partition_id):
        fstab_content = f'''proc            /proc           proc    defaults          0       0
PARTUUID=3a90e54f-01  /boot           vfat    defaults          0       2
PARTUUID=3a90e54f-02  /               ext4    defaults,noatime  0       1
# a swapfile is not a swap partition, no line here
#   use  dphys-swapfile swap[on|off]  for that
/dev/{partition_id} /mnt/usb auto auto,user,nofail,noatime,rw,uid=pi,gid=pi 0 0
'''
        with open('./fstab', 'w') as f:
            f.write(fstab_content)
       
        cmd = 'sudo cp -f ./fstab /etc/fstab'
        cp = run(cmd, shell=True)
        if not cp.returncode:
            self.usb_status['try_adapt_fstab']['status'] = True
            self.usb_status['try_adapt_fstab']['msg'] = f'modify /etc/fstab for {partition_id}'
        else:
            self.usb_status['try_adapt_fstab']['msg'] = f'modify /etc/fstab failed.'

    def check_mount_folder(self):
        cp = run(f'ls {self.mount_folder}',
                           shell=True, stdout=DEVNULL)
        self.usb_status['mount_folder_exists']['status'] = True
        if not cp.returncode:
            self.usb_status['mount_folder_exists']['msg'] = f'{self.mount_folder} ready for mounting.'
        else:
            run(f'sudo mkdir {self.mount_folder}', shell=True)
            self.usb_status['mount_folder_exists']['msg'] = f'{self.mount_folder} created for mounting.'

    def check_usb_mount(self):
        cp = run(
            f"mount -l | grep {self.usb_status['partition_id']['status']}", shell=True, stdout=DEVNULL)
        if not cp.returncode:
            self.usb_status['usb_drive_mounted']['status'] = True
            self.usb_status['usb_drive_mounted']['msg'] = 'USB drive is mounted.'
            self.usb_status['try_mount_usb']['status'] = True
        else:
            self.usb_status['usb_drive_mounted']['status'] = False
            self.usb_status['usb_drive_mounted']['msg'] = 'USB drive is not mounted. Trying to mount ...'
            self.try_mount_usb()

    def try_mount_usb(self):
        cp = run(f'sudo mount -a', shell=True, stdout=DEVNULL, stderr=DEVNULL)
        if not cp.returncode:
            self.usb_status['try_mount_usb']['status'] = True
            self.usb_status['try_mount_usb']['msg'] = 'USB drive mounted successfully'
        else:
            self.usb_status['try_mount_usb']['status'] = False
            self.usb_status['try_mount_usb']['msg'] = 'Can\'t mount usb drive, maybe some problem with /etc/fstab.'

    def check_output_folder(self):
        if self.usb_status['try_mount_usb']['status'] == False:
            return

        if not self.output_folder.exists():
            try:
                self.output_folder.mkdir()
            except PermissionError as e:
                logging.debug(f'{e.__class__}: {e}')
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
            cam.start_recording(str(self.h264_files['recording']))
            self.timestamp_filename = self.clip_start_time.strftime(
                '%Y%m%d_%H-%M-%S')
            logging.info(
                f'Start recording clip {self.clip_count} at {self.clip_start_time.strftime("%Y-%m-%d %H:%M:%S")}, duration: {self.duration} secs')

        with picamera.PiCamera() as cam:
            cam.resolution = self.resolution
            cam.annotate_background = picamera.Color('black')
            cam.framerate = self.fps
            cam.start_preview()

            start_recording_session()

            while True:
                if not self.button.is_pressed:
                    logging.debug('Button released.')
                    logging.info('Stop recording ...')
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
                cam.wait_recording(0.9)
                # time.sleep(0.8)

    def clean_up_mp4box_log(self, MP4Box_temp_log, count):
        with open(MP4Box_temp_log, 'r') as f:
            lines = f.readlines()

        target_pattern = re.compile(r'AVC Import results: (\d*) samples')
        for line in lines:
            if target_pattern.match(line):
                logging.info(f'Clip {count} info: {line.strip()}')
        
        MP4Box_temp_log.unlink()

    def convert_video(self, file, timestamp, count):
        self.converting_video += 1
        logging.info(f'Start converting Clip {count} ...')
        output = self.output_folder.joinpath(f'{timestamp}.mp4')
        MP4Box_temp_log = Path(f'./logs/temp_log_{timestamp}')
        cp = run(
            ["MP4Box", "-add", f'{file}:fps={self.fps}', output], stdout=DEVNULL, stderr=open(MP4Box_temp_log, 'a'))
        if cp.returncode:
            logging.error(f'Clip {count} convert failed.')
            # sys.exit(1)
        else:
            logging.info(
                f'Clip {count} convert done. Mp4 file saved to {output.name}.')
            file.unlink()

        self.converting_video -= 1
        self.clean_up_mp4box_log(MP4Box_temp_log, count)

        if not self.button.is_pressed and self.converting_video == 0:
            logging.info('Standby for recording ...')

    def check_ready_for_recording(self):
        for key, values in self.usb_status.items():
            if not values['status']:
                self.ready_for_recording = False
                return
            self.ready_for_recording = True

    def log_usb_status(self):
        # check any diff
        if self.usb_status_changed:
            self.usb_status_changed_list = []
            for key, values in self.usb_status.items():
                if values != self.last_usb_status[key]:
                    self.usb_status_changed_list.append(key)

            for key, values in self.usb_status.items():
                if not key in self.usb_status_changed_list:
                    continue
                if not values['msg']:
                    continue

                if values['status']:
                    logging.info(values['msg'])
                else:
                    logging.error(values['msg'])

            self.show_msg = True

        self.last_usb_status = deepcopy(self.usb_status)

    @property
    def usb_status_changed(self):
        return not self.usb_status == self.last_usb_status

    def run(self):
        logging.info('PiGGCam starting ...')
        logging.info(f'Video spec: {self.resolution} at {self.fps} fps, duration: {self.duration} secs')

        while True:
            self.GGCam_init()

            # check if everything is ready
            self.check_ready_for_recording()

            if self.button.is_pressed and self.ready_for_recording and self.converting_video == 0:
                logging.debug('Button pressed for start recording.')
                self.record()
            else:
                if self.show_msg and self.ready_for_recording:
                    logging.info('Standby for recording ...')
                    self.show_msg = False

            time.sleep(1)

if __name__ == '__main__':
    a = GGCam()
    a.check_usb_partition_id()
