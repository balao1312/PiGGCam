#!/usr/bin/python3

import json

resolution_choice = input('1. Video resolution choices:\n\n\t1: 1920x1080,30p\n\t2: 1280x720,60p\n\t3: 1280x720,30p.\n\n\tYour choice: ')

res_dic = {
    '1': ((1920, 1080), 30),
    '2': ((1280, 720), 30),
    '3': ((1280, 720), 60),
}

duration = int(input('\n2. Duration (secs) of each clips: '))

config = {
    'fps': res_dic[resolution_choice][1],
    'resolution': res_dic[resolution_choice][0],
    'duration': duration,
    'mount_folder': '/mnt/usb',
    'output_folder': '/mnt/usb/videos',
}

with open('config.py', 'w') as f:
    f.write(f'config = {json.dumps(config)}')
# print(json.dumps(config))
