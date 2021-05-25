#!/usr/bin/python3

import pprint
import subprocess
import sys

def clean_screen():
    cp = subprocess.run('clear')

# resulotion
res_dic = {
    '1': ((1920, 1080), 30),
    '2': ((1280, 720), 60),
    '3': ((1280, 720), 30),
}

print('==> Video resolution choices:\n\t1: 1920x1080,30p\n\t2: 1280x720,60p\n\t3: 1280x720,30p\n')
while 1:
    resolution_choice = input('\tYour choice: ')

    if resolution_choice in ['1', '2', '3']:
        break
    else:
        print('Please input 1, 2, or 3.')
clean_screen()

# duration
print('==> Please input duration(secs) of each clips.\n')
while 1:
    try:
        duration = int(input('\tduration(secs): '))
        if duration < 30 or duration > 900:
            print('value must in range 30 ~ 900 secs')
            continue
        break
    except KeyboardInterrupt:
        print()
        sys.exit()
    except:
        print('value is not interger')
        continue
clean_screen()

# output file location
print('==> Please choose where to save output files:\n\t1: sd card\n\t2: usb drive.')
print('==> Note: Choose SD card may cause frame dropping issue.\n')
while 1:
    output_choice = input('\toutput_location: ')
    if output_choice in ['1', '2']:
        break
    else:
        print('Please input 1 or 2.')
        continue

output_location = 'sd card' if output_choice == '1' else 'usb drive'
print(f'==> output videos will save to: {output_location}')
clean_screen()

# record mode
print('==> Please choose record mode:\n\t1: non-stop recording\n\t2: motion detect recording.\n')
while 1:
    output_choice = input('\trecord mode: ')
    if output_choice in ['1', '2']:
        break
    else:
        print('Please input 1 or 2.')
        continue

record_mode = 'non-stop' if output_choice == '1' else 'motion'
print(f'==> record mode is set to: {record_mode}')
clean_screen()

# if record mode == motion
if record_mode == 'motion':
    print('==> Please input motion detection interverl(secs):\n')
    while 1:
        try:
            motion_interval = int(input('\tintervals(secs): '))
            if motion_interval < 60 or motion_interval > 300:
                print('value must be > 60 secs and < 300 secs')
                continue
            break
        except KeyboardInterrupt:
            print()
            sys.exit()
        except:
            print('value is not interger')
            continue

    print(f'==> motion_interval: {motion_interval} secs')
else:
    motion_interval = 0
clean_screen()


# -------------------------------------------------------------------------------------------------------------------
print(f'==> resolution selected: {res_dic[resolution_choice]}')
print(f'==> duration: {duration} secs')

config = {
    'fps': res_dic[resolution_choice][1],
    'resolution': res_dic[resolution_choice][0],
    'duration': duration,
    'output_location': output_location,
    'record_mode': record_mode,
    'motion_interval': motion_interval,
}

with open('config.py', 'w') as f:
    f.write(f'config = {pprint.pformat(config)}')

print('Setting updated.')
