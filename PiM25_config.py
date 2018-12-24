import re
import os

# Device information
APP_ID = "PiM25"
DEVICE = "Raspberry Pi 3B+"
DEVICE_ID = "DEVICE_ID1234"
DEVICE_IP = ''

# Restful_API
env_file = open("/home/pi/Local/env.txt").readlines()
Restful_URL = env_file[0][5:].replace("\n", "")
Restful_interval = 60           # 60 seconds
float_re_pattern = re.compile("^-?\d+\.\d+$")
num_re_pattern = re.compile("^-?\d+\.\d+$|^-?\d+$")

# MAC address
mac = open('/sys/class/net/eth0/address').readline().upper().strip()
DEVICE_ID = mac.replace(':','') 
print(DEVICE_ID)

# Tick time
with open('/proc/uptime', 'r') as f:
    try:
        tick = float(f.readline().split()[0])
    except:
        print "Error: reading /proc/uptime"

# Other parameters
fmt_opt = 0
ver_format = 3
gps_fix = 1
ver_app = "0.0.1"
FAKE_GPS = 0

