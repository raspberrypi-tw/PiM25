import re
import os
import commands

# Device information
APP_ID = "PiM25"
DEVICE = "Raspberry_Pi"
G5T_GPIO = 23
GPS_GPIO = 24
DEVICE_IP = commands.getoutput("hostname -I")
data_path = "/home/pi/Data/"

# Restful_API
env_file = open("/home/pi/Local/env.txt").readlines()
Restful_URL = env_file[0].split(",")[1].replace("\n", "")

# MAC address
mac = open('/sys/class/net/eth0/address').readline().upper().strip()
DEVICE_ID = mac.replace(':','') 

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

