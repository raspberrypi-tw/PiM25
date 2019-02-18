#!/bin/bash

OTA="$(sudo grep -Po 'OTA: \K.*' /home/pi/Local/env.txt)"

sleep 30
[ -f /home/pi/PiM25/PiM25.py ] && {
    /usr/bin/sudo git -C /home/pi/PiM25 fetch --all
    /usr/bin/sudo git -C /home/pi/PiM25 reset --hard origin/sinica
    # /usr/bin/sudo nohup python -u /home/pi/PiM25/PiM25.py &
    # /usr/bin/sudo killall -o 1d python &
} || {
    /usr/bin/sudo git clone OTA /home/pi/PiM25
    /usr/bin/sudo git checkout sinica
    # /usr/bin/sudo nohup python -u /home/pi/PiM25/PiM25.py &
    # /usr/bin/sudo killall -o 1d python &
}

