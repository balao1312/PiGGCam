# import RPi.GPIO as GPIO
# import picamera
from config import config
from datetime import datetime
from subprocess import call, DEVNULL, check_output, STDOUT
import time
from pathlib import Path
import sys
import re


class GGCam():

    interval = config['interval']
    temp_h264_file_location = config['temp_h264_file_location']
    output_mp4_folder = config['output_mp4_folder']
    partition_id = config['partition_id']

    def __init__(self):
        # check if there is any USB drive and get USB drive partition table (gpt or dos)
        usb_partition_table = self.check_usb_partition_table()
        if usb_partition_table:
            print(f'==> USB drive partition table is : {usb_partition_table}')
        else:
            print('==> no USB drive found. exited.')
            sys.exit(1)

        # check if usb is mounted
        if self.check_usb_mount():
            self.is_usb_mounted = True
            print('==> USB drive already mounted.')
        else:
            self.is_usb_mounted = False
            print('==> USB drive not mounted.')
            self.try_mount_usb()
    
    def check_usb_mount(self):
        exited_code = call(f'mount -l | grep {self.partition_id}', shell=True, stdout=DEVNULL, stderr=DEVNULL)
        return False if exited_code else True

    def check_usb_partition_table(self):
        cmd = f'sudo /usr/sbin/fdisk -l | grep -n4 {self.partition_id}'
        try:
            output = check_output([cmd], timeout=3, stderr=STDOUT, shell=True).decode('utf8')
            target = re.compile(r'Disklabel type: (.*)')
            result = target.search(output)
            return result.group(1)
        except:
            return None

    def try_mount_usb(self):
        print('==> trying to mount USB drive ...')
        exited_code = call('sudo mount -a', shell=True, stdout=DEVNULL, stderr=DEVNULL)
        if exited_code:
            print('==> USB drive mount failed.')
        else:
            print('==> USB drive mounted successfully')
        
    def run(self):
        print('Now running')
