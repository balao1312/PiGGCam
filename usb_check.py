from subprocess import DEVNULL, check_output, STDOUT, run
from datetime import datetime
from copy import deepcopy
from pathlib import Path
import logging
import re


class Usb_check():
    usb_status_changed_list = []
    mount_folder = Path('/mnt/usb')
    output_folder = mount_folder.joinpath('videos')

    def __init__(self):
        self.usb_status = self.usb_status_initiated
        self.last_usb_status = deepcopy(self.usb_status)
    
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
            }, 'try_adapt_fstab': {
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

    def usb_check(self):
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
                self.usb_status['output_folder_exists']['status'] = True
            except PermissionError as e:
                logging.debug(f'{e.__class__}: {e}')
                self.usb_status['output_folder_exists']['msg'] = f'Can\'t create {self.output_folder} folder.'
                return
            self.usb_status['output_folder_exists']['msg'] = f'{self.output_folder} created for output.'
        else:
            self.usb_status['output_folder_exists']['status'] = True
            self.usb_status['output_folder_exists']['msg'] = f'{self.output_folder} already exists.'

        
    def log_usb_status(self):
        # check any diff
        if self.is_usb_status_changed:
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

        self.last_usb_status = deepcopy(self.usb_status)

    @property
    def is_ready_for_recording(self):
        for key, values in self.usb_status.items():
            if not values['status']:
                return False
            return True
        
    @property
    def is_usb_status_changed(self):
        return not self.usb_status == self.last_usb_status
