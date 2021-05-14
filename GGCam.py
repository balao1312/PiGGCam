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

from usb_check import Usb_check


class GGCam():
    clip_count = 0
    clip_start_time = None
    timestamp_filename = None
    show_msg = True
    converting_video = 0
    disk_usage_full = False

    button = gpiozero.Button(23)
    led_standby = gpiozero.LED(24)
    led_recording = gpiozero.LED(4)
    recording = False
    
    def __init__(self):
        # logging stuff
        self.log_folder = Path('./logs')
        if not self.log_folder.exists():
            self.log_folder.mkdir()

        logging_file = self.log_folder.joinpath(
            f'{datetime.now().strftime("%Y-%m-%d")}.log')

        logging_format = '[%(asctime)s] %(levelname)s: %(message)s'
        logging_datefmt = '%Y-%m-%d %H:%M:%S'
        logging.basicConfig(level=logging.DEBUG, format=logging_format, datefmt=logging_datefmt,
            handlers=[logging.FileHandler(logging_file), logging.StreamHandler()])

        # config stuff
        self.load_config_from_file()

        # output folder check: sd card or usb
        if self.output_location == 'sd card':
            self.output_folder = Path('/home/pi/videos')
            if not self.output_folder.exists():
                self.output_folder.mkdir()
            
            self.temp_h264_folder = Path('./temp')
            if not self.temp_h264_folder.exists():
                self.temp_h264_folder.mkdir()

        elif self.output_location == 'usb drive':
            self.output_folder = Path('/mnt/usb/videos')

            self.temp_h264_folder = Path('/mnt/usb/temp')
            if not self.temp_h264_folder.exists():
                self.temp_h264_folder.mkdir()

        self.h264_files = {
            'recording': self.temp_h264_folder.joinpath('temp1.h264'),
            'done': self.temp_h264_folder.joinpath('temp2.h264'),
        }

        self.usb_checker = Usb_check()

        self.led_standby.on()
    
    def GGCam_exit(self):
        logging.info('program ended.')
        self.led_standby.off()
    
    def load_config_from_file(self):
        try:
            self.duration = config['duration']
            self.output_location = config['output_location']  # sd card or usb drive
            self.fps = config['fps']
            self.resolution = config['resolution']
        except Exception as e:
            logging.error(f'something wrong with config.py. {e.__class__}: {e}')
            logging.info(f'please run setup.py.')
            sys.exit(1)

    def swap_h264_set(self):
        self.h264_files['recording'], self.h264_files['done'] = self.h264_files['done'], self.h264_files['recording']

    @property
    def disk_usage(self):
        cmd = "df | grep -P root | awk '{print $5}'"
        try:
            output = check_output([cmd], stderr=STDOUT, shell=True).decode('utf8').strip()
            return int(output[:-1])
        except Exception as e:
            logging.error(f'something wrong with disk_usage. {e.__class__}: {e}')
    
    def blink_led(self):
        logging.debug('led ready to blink')
        while 1:
            if self.recording:
                self.led_recording.on()
                time.sleep(0.5)
                self.led_recording.off()
                time.sleep(0.5)
            else:
                time.sleep(1)

    def record(self):
        # avoiding show two times standby msg if directly into record process from program start
        self.show_msg = False

        th_blink = threading.Thread(target=self.blink_led)
        th_blink.start()

        def start_recording_session():
            self.recording = True
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
                if self.disk_usage > 98:
                    cam.stop_recording()
                    self.recording = False
                    logging.error(f'Disk usage is almost full. stop recording.')
                    th_3 = threading.Thread(target=self.convert_video, args=(
                        self.h264_files['recording'], self.timestamp_filename, self.clip_count))
                    th_3.start()
                    th_3.join()
                    sys.exit(1)

                if not self.button.is_pressed:
                    logging.debug('Button released.')
                    logging.info('Stop recording ...')
                    cam.stop_recording()
                    self.recording = False
                    th_2 = threading.Thread(target=self.convert_video, args=(
                        self.h264_files['recording'], self.timestamp_filename, self.clip_count))
                    th_2.start()
                    th_2.join()
                    return

                if (datetime.now() - self.clip_start_time).seconds >= self.duration:
                    logging.debug(f'Disk usage: {self.disk_usage}%')
                    cam.stop_recording()
                    self.recording = False

                    # swap recording file and done recored file refference
                    self.swap_h264_set()

                    # start another thread to convert done recorded file
                    th_1 = threading.Thread(target=self.convert_video, args=(
                        self.h264_files['done'], self.timestamp_filename, self.clip_count))
                    th_1.start()

                    # record another clip
                    start_recording_session()

                cam.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cam.wait_recording(0.9)

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
        else:
            logging.info(
                f'Clip {count} convert done. Mp4 file saved to {output.name}.')
            file.unlink()

        self.converting_video -= 1
        self.clean_up_mp4box_log(MP4Box_temp_log, count)

        if not self.button.is_pressed and self.converting_video == 0:
            logging.info('Standby for recording ...')

    def run(self):
        logging.info('PiGGCam starting ...')
        logging.info(f'Video spec: {self.resolution} at {self.fps} fps, duration: {self.duration} secs')
        logging.info(f'Video will save to {self.output_folder}')

        while True:
            if self.disk_usage_full:
                time.sleep(2)
                continue

            if self.output_location == 'usb drive':
                self.usb_checker.usb_check()

                if self.usb_checker.is_usb_status_changed:
                    self.show_msg = True

                if self.button.is_pressed and self.usb_checker.is_ready_for_recording and self.converting_video == 0:
                    logging.debug('Button pressed.')
                    self.record()
                else:
                    if self.show_msg and self.usb_checker.is_ready_for_recording:
                        logging.info('Standby for recording ...')
                        self.show_msg = False

            elif self.output_location == 'sd card':
                if self.disk_usage >= 98:
                    logging.error('Disk usage full, please check destination disk.')
                    self.disk_usage_full = True
                    # TODO turn error led on
                    continue

                if self.button.is_pressed and self.converting_video == 0:
                    logging.debug('Button pressed for start recording.')
                    self.record()
                else:
                    if self.show_msg :
                        logging.info('Standby for recording ...')
                        self.show_msg = False

            time.sleep(2)

if __name__ == '__main__':
    aa = GGCam()
    print(aa.disk_usage)
