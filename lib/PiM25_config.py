import re
import os
import commands

G5T_GPIO = 23
GPS_GPIO = 24
DEVICE_IP = commands.getoutput("hostname -I")
data_path = "/home/pi/Data_CSV/"

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


# Device information
device_info = { "CFPM1.0"   : -1, \
                "CFPM2.5"   : -1, \
                "CFPM10"    : -1, \
                "s_d0"      : -1, \
                "s_d1"      : -1, \
                "s_d2"      : -1, \
                "s_t0"      : -1, \
                "s_h0"      : -1, \
                "date"      : "", \
                "time"      : "", \
                "gps_num"   : -1, \
                "gps_lat"   : -1, \
                "gps_lon"   : -1, \
                "app"       : "PiM25", \
                "device"    : "Raspberry_Pi", \
                "device_id" : "", \
                "tick"      : -1, \
                "fmt_opt"   : 0, \
                "ver_format": 3, \
                "gps_fix"   : 1, \
                "ver_app"   : "0.0.1", \
                "FAKE_GPS"  : 0
              }

