#!/usr/bin/python3 

from GGCam import GGCam
import sys
import os

if __name__ == '__main__':
    runner = GGCam()
    try:
        runner.run()
    except KeyboardInterrupt:
        print('\n==> Interrupted.')
        runner.GGCam_exit()
        try:
            print('\n==> Exited')
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    # except Exception as e:
        # print(f'==> main func error: {e.__class__} {e}')
