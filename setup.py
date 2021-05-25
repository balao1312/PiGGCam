#!/usr/bin/python3

import pprint
import subprocess
import sys


class PiGGCam_Config():

    def clean_screen(self):
        subprocess.run('clear')

    def clean_deco(func):
        def wrapper(self, *arg, **kwarg):
            self.clean_screen()
            result = func(self, *arg, **kwarg)
            return result
        return wrapper

    @clean_deco
    def set_resolution(self):
        res_dic = {
            '1': ((1920, 1080), 30),
            '2': ((1280, 720), 60),
            '3': ((1280, 720), 30),
        }

        print('Video resolution choices:\n\n\t1: 1920x1080, 30p\n\t2:  1280x720, 60p\n\t3:  1280x720, 30p\n')
        while 1:
            resolution_choice = input('\n\tYour choice: ')
            if resolution_choice in ['1', '2', '3']:
                break
            else:
                print('Please input 1, 2, or 3.')
        return res_dic[resolution_choice]

    @clean_deco
    def set_duration(self):
        print('Please input max duration(secs) of each clips.\n\t* range: 30 secs ~ 900 secs\n')
        while 1:
            try:
                duration = int(input('\n\tduration(secs): '))
                if duration < 30 or duration > 900:
                    print('\nDuration value must in range 30 ~ 900 secs')
                    continue
                break
            except KeyboardInterrupt:
                print()
                sys.exit()
            except:
                print('\nPlease input a number')
                continue
        return duration

    @clean_deco
    def set_output_location(self):
        print('Please choose where to save output files:\n\n\t1: sd card\t* may cause frame dropping issue.\n\t2: usb drive.\n')
        while 1:
            output_choice = input('\n\toutput_location: ')
            if output_choice in ['1', '2']:
                break
            else:
                print('Please input 1 or 2.')
                continue
        return 'sd card' if output_choice == '1' else 'usb drive'

    @clean_deco
    def set_record_mode(self):
        print('Please choose record mode:\n\n\t1: non-stop recording\n\t2: motion detect recording.\n')
        while 1:
            output_choice = input('\n\trecord mode: ')
            if output_choice in ['1', '2']:
                break
            else:
                print('Please input 1 or 2.')
                continue

        self.record_mode = 'non-stop' if output_choice == '1' else 'motion'
        return self.record_mode

    @clean_deco
    def set_motion_interval(self):
        if self.record_mode == 'motion':
            print('Please input motion detection interverl(secs):\n')
            print('* Description: \n\tStop recording signal will be sent if no movement detected within this time interval past.\n\trange: 60 secs ~ 300 secs\n')
            while 1:
                try:
                    motion_interval = int(input('\n\tintervals(secs): '))
                    if motion_interval < 60 or motion_interval > 300:
                        print('\nMotion detection interval must be in range 60 secs ~ 300 secs')
                        continue
                    break
                except KeyboardInterrupt:
                    print()
                    sys.exit()
                except:
                    print('\nPlease input a number')
                    continue
            return motion_interval
        else:
            return 0

    @clean_deco
    def do_config(self):
        resolution = self.set_resolution()
        self.config = {
            'resolution': resolution[0],
            'fps': resolution[1],
            'duration': self.set_duration(),
            'output_location': self.set_output_location(),
            'record_mode': self.set_record_mode(),
            'motion_interval': self.set_motion_interval(),
        }

    @clean_deco
    def show_config(self):
        print(f'''Your configures are list below:

        Resolution:             {self.config['resolution'][0]} x {self.config['resolution'][1]}
        Frames Per Second:      {self.config['fps']} 
        Duration:               {self.config['duration']} secs
        Output Location:        {self.config['output_location']}
        Record Mode:            {self.config['record_mode']}
        Motion Detect Interval: {self.config['motion_interval']} secs        # set to 0 if record mode = non-stop

        ''')

    @clean_deco
    def run(self):
        while 1:
            self.do_config()
            self.show_config()

            is_confirmed = input('\tConfirm and Save? (y/n):')
            if is_confirmed == 'y':
                break
            else:
                do_reset = input('\n\tRedo config? (y/n):')
                if do_reset == 'y':
                    continue
                else:
                    print('\n\nLeaving without any change.')
                    return

        with open('config.py', 'w') as f:
            f.write(f'config = {pprint.pformat(self.config)}')

        print('\n\n==> Config updated.')


if __name__ == '__main__':
    configurer = PiGGCam_Config()
    configurer.run()
