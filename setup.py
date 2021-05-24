#!/usr/bin/python3

import pprint

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

print(f'==> resolution selected: {res_dic[resolution_choice]}')
print('=' * 80)


# duration
print('==> Please input duration(secs) of each clips.\n')
while 1:
    try:
        duration = int(input('\tduration(secs): '))
        if duration < 1 or duration > 900:
            print('value must be positive ,non zero, and smaller than 900 (15min)')
            continue
        break
    except:
        print('value is not interger')
        continue

print(f'==> duration: {duration} secs')
print('=' * 80)


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
print('=' * 80)


config = {
    'fps': res_dic[resolution_choice][1],
    'resolution': res_dic[resolution_choice][0],
    'duration': duration,
    'output_location': output_location,
}

with open('config.py', 'w') as f:
    f.write(f'config = {pprint.pformat(config)}')

print('Setting updated.')
print('=' * 80)
