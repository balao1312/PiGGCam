import subprocess
import re

def check():
        cmd = 'sudo /usr/sbin/fdisk -l | grep -n4 sdb'
        output = subprocess.check_output(
            [cmd], timeout=3, stderr=subprocess.STDOUT, shell=True).decode('utf8')

        target = re.compile(r'Disklabel type: (.+)')
        result = target.search(output)
        print(result.group(1))
check()
