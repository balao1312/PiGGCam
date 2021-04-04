#!/usr/bin/expect 

spawn udisksctl mount -b /dev/sda1
expect "Password: "
send "raspberry\n"
expect eof
