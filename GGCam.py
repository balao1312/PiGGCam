import gpiozero
import picamera

from config import config
from datetime import datetime
from subprocess import DEVNULL, check_output, STDOUT, run
from pathlib import Path
from copy import deepcopy, copy
import threading
import logging
import time
import sys
import re

from usb_util import Usb_check


class GGCam():
    clip_count = 0
    clip_start_time = None
    timestamp_filename = None
    show_msg = True
    converting_video = 0
    disk_usage_full = False
    is_motion = False
    is_recording = False

    button = gpiozero.Button(23)
    led_standby = gpiozero.LED(24)
    led_status = gpiozero.LED(4)
    led_recording = gpiozero.LED(19)
    pir = gpiozero.MotionSensor(21)

    def __init__(self):
        self.log_folder = Path('./logs')
        if not self.log_folder.exists():
            self.log_folder.mkdir()
        self.onoff_file = Path('./onoff')
        if not self.onoff_file.exists():
            self.onoff_file.touch()
            with open(self.onoff_file, 'w') as f:
                f.write('0')

        self.logging_file_renew()
        self.load_config_from_file()
        self.set_output_config()
        self.clean_h264_folder()

        if self.output_location == 'usb drive':
            self.usb_checker = Usb_check()

        self.led_standby.on()

        # create a thread for blinking led according to recording status
        thread_blink_when_recording = threading.Thread(
            target=self.blink_led_when_recording)
        thread_blink_when_recording.start()

        # create a thread for led according to converting or error status
        thread_led_show_converting_or_error = threading.Thread(
            target=self.led_show_converting_or_error)
        thread_led_show_converting_or_error.start()

        if self.record_mode == 'motion':
            thread_motion_detect = threading.Thread(target=self.motion_detect)
            thread_motion_detect.start()

    def clean_h264_folder(self):
        for each_file in self.temp_h264_folder.iterdir():
            each_file.unlink()

        logging.debug('H264 folder cleaned.')

    @property
    def trigger(self):
        if self.record_mode == 'non-stop':
            return self.button.is_pressed
        elif self.record_mode == 'motion':
            return self.is_motion
        elif self.record_mode == 'testing':
            return self.get_on_off_from_file

    @property
    def get_on_off_from_file(self):
        with open('./onoff', 'r') as f:
            on_or_off = f.read()
        return int(on_or_off)

    def logging_file_renew(self):
        # delete existing handler and renew, for log to new file if date changes
        logger = logging.getLogger()
        for each in logger.handlers[:]:
            logger.removeHandler(each)

        logging_file = self.log_folder.joinpath(
            f'{datetime.now().strftime("%Y-%m-%d")}.log')
        logging_format = '[%(asctime)s] %(levelname)s: %(message)s'
        logging_datefmt = '%Y-%m-%d %H:%M:%S'
        logging.basicConfig(level=logging.DEBUG, format=logging_format, datefmt=logging_datefmt,
                            handlers=[logging.FileHandler(logging_file), logging.StreamHandler()])

    def load_config_from_file(self):
        try:
            self.duration = config['duration']
            # sd card or usb drive
            self.output_location = config['output_location']
            self.fps = config['fps']
            self.resolution = config['resolution']
            self.record_mode = config['record_mode']
            self.motion_interval = config['motion_interval']
        except Exception as e:
            logging.error(
                f'something wrong with config.py. {e.__class__}: {e}')
            logging.info(f'please run setup.py.')
            sys.exit(1)

    def set_output_config(self):
        '''
        there are total 3 location must set:
        1. recording .h264 file
        2. coverting temp file
        3. final output file        
        '''

        # 1. set recording h264 file folder
        self.temp_h264_folder = Path('/mnt/ramdisk')    # best sulotion
        # self.temp_h264_folder = self.output_folder  # depends on output location
        # self.temp_h264_folder = Path('/home/pi')  # may cause frame dropping

        # 2. set converting temp file folder
        self.converting_temp_folder = Path('/mnt/ramdisk')  # best sulotion
        # self.converting_temp_folder = self.output_folder  # depends on output location

        # 3.determine final output file folder
        if self.output_location == 'sd card':
            self.output_folder = Path('/home/pi/videos')
            if not self.output_folder.exists():
                self.output_folder.mkdir()

        elif self.output_location == 'usb drive':
            self.output_folder = Path('/mnt/usb/videos')

    def GGCam_exit(self):
        logging.info('program ended.')
        self.led_standby.off()
        self.is_recording = False
        self.led_status.off()
        time.sleep(1)

    def check_disk_usage(self):
        if self.output_location == 'usb drive':
            partition_id = self.usb_checker.usb_status['partition_id']['status']
            cmd = f"df | grep -P {partition_id} | awk '{{print $5}}'"
        elif self.output_location == 'sd card':
            cmd = "df | grep -P root | awk '{print $5}'"

        try:
            output = check_output([cmd], stderr=STDOUT,
                                  shell=True).decode('utf8').strip()
            self.disk_usage = int(output[:-1])
        except Exception as e:
            logging.error(
                f'something wrong with checking disk_usage. {e.__class__}: {e}')

        logging.debug(f'Output disk usage is {self.disk_usage} %')

        if self.disk_usage >= 98:
            logging.error(f'Disk usage is almost full. stop recording.')
            self.disk_usage_full = True

    def led_show_converting_or_error(self):
        logging.debug('led for showing converting or error is ready.')
        while 1:
            if self.converting_video > 0:
                self.led_status.on()
                time.sleep(0.5)
                self.led_status.off()
                time.sleep(0.5)
            else:
                time.sleep(1)

            if self.disk_usage_full:
                self.led_status.on()
                while 1:
                    time.sleep(10)

    def blink_led_when_recording(self):
        logging.debug('led for recording status is ready.')
        while 1:
            if self.is_recording:
                self.led_recording.on()
                time.sleep(0.5)
                self.led_recording.off()
                time.sleep(0.5)
            else:
                time.sleep(1)

    def motion_detect(self):
        logging.debug('PIR Motion detection started.')
        self.last_motion_countdown = self.motion_interval
        show_one_time = True
        while 1:
            if self.pir.motion_detected:
                if show_one_time:
                    logging.info(
                        f'Motion detected: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
                    show_one_time = False

                self.last_motion_countdown = self.motion_interval
                self.is_motion = True

            if self.last_motion_countdown == 0:
                show_one_time = True
                if show_one_time:
                    logging.info(
                        f'No motion detected in {self.motion_interval} secs.')

                self.is_motion = False

            # print(self.last_motion_countdown, self.is_motion)
            if self.last_motion_countdown > -1:
                self.last_motion_countdown -= 1

            time.sleep(1)

    def record(self):
        def clip_renew():
            self.clip_count += 1
            self.clip_start_time = datetime.now()
            self.clip_start_time_string = self.clip_start_time.strftime(
                ("%Y-%m-%d_%H_%M_%S"))
            self.clip_file_object = self.temp_h264_folder.joinpath(
                f'{self.clip_start_time_string}.h264')

        def start_recording_session():
            self.check_disk_usage()
            if self.disk_usage_full:
                return

            clip_renew()
            self.is_recording = True
            cam.start_recording(str(self.clip_file_object))
            logging.info(
                f'Start recording clip {self.clip_count} at {self.clip_start_time.strftime("%Y-%m-%d %H:%M:%S")}, max duration: {self.duration} secs')

        def split_recording():
            self.check_disk_usage()
            if self.disk_usage_full:
                return

            self.done_recorded = copy(self.clip_file_object)
            last_clip_count = self.clip_count
            clip_renew()
            logging.info(
                f'Start recording clip {self.clip_count} at {self.clip_start_time.strftime("%Y-%m-%d %H:%M:%S")}, max duration: {self.duration} secs')
            cam.split_recording(str(self.clip_file_object))

            # start another thread to convert done recorded file
            th_1 = threading.Thread(target=self.convert_video, args=(
                self.done_recorded, last_clip_count))
            th_1.start()

        def stop_recording_session():
            logging.info('Stop recording ...')
            cam.stop_recording()
            self.is_recording = False
            self.convert_video(self.clip_file_object, self.clip_count)

        # avoiding show two times standby msg if directly into record process from program start
        self.show_msg = False

        with picamera.PiCamera() as cam:
            cam.resolution = self.resolution
            cam.annotate_background = picamera.Color('black')
            cam.framerate = self.fps
            cam.start_preview()

            start_recording_session()

            while True:
                if self.disk_usage_full:
                    self.is_recording = False
                    return

                if not self.trigger:
                    logging.debug('Trigger is off.')
                    stop_recording_session()
                    return

                if (datetime.now() - self.clip_start_time).seconds >= self.duration:
                    split_recording()
                    self.logging_file_renew()

                cam.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                time.sleep(1)

    def convert_video(self, file_object, count):
        time.sleep(1)
        self.converting_video += 1
        logging.info(f'Start converting Clip {count} ...')
        ts = file_object.stem
        output = self.output_folder.joinpath(f'{ts}.mp4')
        MP4Box_temp_log = Path(f'./logs/temp_log_{ts}')
        cp = run(
            ["MP4Box", "-tmp", f"{self.converting_temp_folder}", "-add", f'{file_object}:fps={self.fps}', output], stdout=DEVNULL, stderr=open(MP4Box_temp_log, 'a'))
        if cp.returncode:
            logging.error(f'Clip {count} convert failed.')
        else:
            logging.info(
                f'Clip {count} convert done.')
            file_object.unlink()

        self.converting_video -= 1
        self.clean_up_mp4box_log(MP4Box_temp_log, count)

        if not self.trigger and self.converting_video == 0:
            logging.info('Standby for recording ...')

    def clean_up_mp4box_log(self, MP4Box_temp_log, count):
        with open(MP4Box_temp_log, 'r') as f:
            lines = f.readlines()

        target_pattern = re.compile(r'AVC Import results: (\d*) samples')
        for line in lines:
            if target_pattern.match(line):
                logging.info(f'Clip {count} info: {line.strip()}')

        MP4Box_temp_log.unlink()

    def run(self):
        logging.info('PiGGCam starting ...')
        logging.info(
            f'Video spec: {self.resolution} at {self.fps} fps, max duration: {self.duration} secs')
        logging.info(f'Video will save to {self.output_folder}')
        logging.info(f'Record mode is: {self.record_mode}')

        while True:
            if self.disk_usage_full:
                time.sleep(2)
                continue

            if self.output_location == 'usb drive':
                self.usb_checker.usb_check()

                if self.usb_checker.is_usb_status_changed:
                    self.show_msg = True

                if self.trigger and self.usb_checker.is_ready_for_recording and self.converting_video == 0 and not self.disk_usage_full:
                    logging.debug('Trigger is on.')
                    self.record()
                else:
                    if self.show_msg and self.usb_checker.is_ready_for_recording and not self.disk_usage_full:
                        logging.info('Standby for recording ...')
                        self.show_msg = False

            elif self.output_location == 'sd card':
                if self.trigger and self.converting_video == 0 and not self.disk_usage_full:
                    logging.debug('Button pressed.')
                    self.record()
                else:
                    if self.show_msg and not self.disk_usage_full:
                        logging.info('Standby for recording ...')
                        self.show_msg = False

            self.logging_file_renew()
            time.sleep(1)
