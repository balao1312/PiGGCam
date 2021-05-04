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
print('==> Please input duration(secs) of each clips.')
while 1:
    try:
        duration = int(input('\tduration(secs): '))
        if duration < 1:
            print('value must be positive and non zero.')
            continue
        break
    except:
        print('value is not interger')
        continue

print(f'==> duration: {duration} secs')
print('=' * 80)


# output file location
print('==> Please choose where to save output files:\n\t1: sd card\n\t2: usb drive.\n')
while 1:
    output_choice = input('\toutput_location: ')
    if output_choice in ['1', '2']:
        break
    else:
        print('Please input 1, or 2.')
        continue

output_location = '/home/pi/videos' if output_choice == '1' else '/mnt/usb/videos'
print(f'==> output videos will save to: {output_location}')
print('=' * 80)


config = {
    'fps': res_dic[resolution_choice][1],
    'resolution': res_dic[resolution_choice][0],
    'duration': duration,
    'output_folder': output_location,
}

with open('config.py', 'w') as f:
    f.write(f'config = {pprint.pformat(config)}')

print('Setting updated.')
print('=' * 80)
