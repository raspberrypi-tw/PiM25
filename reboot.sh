#!/bin/bash

OTA="$(grep -Po 'OTA: \K.*' /home/pi/Local/env.txt)"

sleep 5
[ -f /home/pi/airbox-pi/PiM25.py ] && {
    /usr/bin/sudo git -C /home/pi/airbox-pi fetch origin
    /usr/bin/sudo git -C /home/pi/airbox-pi reset --hard origin/master
    /usr/bin/sudo nohup python -u /home/pi/airbox-pi/PiM25.py &
} || {
    /usr/bin/sudo git clone OTA /home/pi/airbox-pi
    /usr/bin/sudo nohup python -u /home/pi/airbox-pi/PiM25.py &
}

