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

        self.log_folder = Path('./logs')
        if not self.log_folder.exists():
            self.log_folder.mkdir()
        
        self.usb_checker = Usb_check()
    
    def load_config_from_file(self):
        try:
            self.duration = config['duration']
            self.output_folder = Path(config['output_folder'])
            self.fps = config['fps']
            self.resolution = config['resolution']
        except Exception as e:
            logging.error(f'something wrong with config.py. {e.__class__}: {e}')
            logging.info('Exited.')
            # make a reset script for user
            sys.exit(1)

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

    def run(self):
        logging.info('PiGGCam starting ...')
        logging.info(f'Video spec: {self.resolution} at {self.fps} fps, duration: {self.duration} secs')

        while True:
            self.usb_checker.usb_check()

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
    pass