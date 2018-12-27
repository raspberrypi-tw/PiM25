import time
import pigpio
import commands
from datetime import datetime
import PiM25_config as Conf
import os
import re

"""
def dms2dd(degrees, minutes, seconds, direction):
    dd = float(degrees) + float(minutes)/60 + float(seconds)/(60*60);
    if direction == 'S' or direction == 'W':
        dd *= -1
    return round(dd, 6);

def dmm2dd(dir, DMM):
    DMM = str(abs(float(DMM)))
    index = DMM.find(".")
    D = int(DMM[:index-2])
    M = int(DMM[index-2:index])
    S = round(float(DMM[index:]) * 60, 0)
    return dms2dd(D, M, S, dir)
"""

def read_last_gps(GPS_info):
    last_gps = open("/home/pi/Local/gps_info.txt","r")
    temp = last_gps.readlines()[0].replace("\n", "").split(", ")
    GPS_info += '|gps_num=%s' % (temp[0])
    GPS_info += '|gps_lat=%s' % (temp[1])
    GPS_info += '|gps_lon=%s' % (temp[3])
    last_gps.close()
    return GPS_info

def GPS_data_read(lines):
    GPS_info = ""
    try:
        gprmc = [rmc for rmc in lines if "$GPRMC" in rmc]
        gpgga = [gga for gga in lines if "$GPGGA" in gga]

        if len(gprmc) and len(gpgga):   # read correct
            gga = gpgga[0].split(",")
            gdata = gprmc[0].split(",")
            valid = gdata[2]
            if valid is 'A':    # valid status
                print("GPS valid status")
                satellite = int(gga[7])
                status    = gdata[1]
                latitude  = gdata[3]      #latitude
                dir_lat   = gdata[4]      #latitude direction N/S
                longitude = gdata[5]      #longitude
                dir_lon   = gdata[6]      #longitude direction E/W
                speed     = gdata[7]      #Speed in knots
                speed = float(speed) * 1.825
                print "latitude : %s(%s), longitude : %s(%s), speed : %f" %  (latitude , dir_lat, longitude, dir_lon, speed)
                if speed <= 10:     # move slow
                    print("real time gps location")
                    GPS_info += '|gps_num=%f' % (satellite)
                    # GPS_info += '|gps_lat=%s' % (dmm2dd(dir_lat, latitude))
                    # GPS_info += '|gps_lon=%s' % (dmm2dd(dir_lon, longitude))
                    GPS_info += '|gps_lat=%f' % (latitude * 100)
                    GPS_info += '|gps_lon=%f' % (longitude * 100)
                    
                    # store GPS information
                    last_gps = open("/home/pi/Local/gps_info.txt","w") 
                    # last_gps.write(str(satellite) + ", " + str(dmm2dd(dir_lat, latitude)) + ", " + dir_lat + ", " + str(dmm2dd(dir_lon, longitude)) + ", " + dir_lon)
                    last_gps.write(str(satellite) + ", " + str(latitude * 100) + ", " + dir_lat + ", " + str(longitude * 100) + ", " + dir_lon)
                    last_gps.close() 
                else:
                    # won't upload data
                    print("out of speed")
            else:
                print("GPS invalid status")
                # use last gps location
                GPS_info = read_last_gps(GPS_info)
        else:
            print("GPS can't find GPRMC and GPGGA")
            # use last gps location
            GPS_info = read_last_gps(GPS_info)

    except Exception as e:
        print(e)
        # use last gps location
        GPS_info = read_last_gps(GPS_info)

    return GPS_info
        
def bytes2hex(s):
    return "".join("{:02x}".format(c) for c in s)

def G5T_data_read(dstr):
    # data standard style
    standard = "424d001c"
    data_len = 64
    weather = ""
    index = dstr.find(standard)
    if(index == -1 or len(dstr) < 64):
        return weather
    else:
        data_slice = dstr[index : index + data_len]
        print(data_slice)
        weather += '|CFPM1.0=%d' % (int(data_slice[8] + data_slice[9] + data_slice[10] + data_slice[11], 16))        # cf_pm1 
        weather += '|CFPM2.5=%d' % (int(data_slice[12] + data_slice[13] + data_slice[14] + data_slice[15], 16))      # cf_pm2.5
        weather += '|CFPM10=%d' % (int(data_slice[16] + data_slice[17] + data_slice[18] + data_slice[19], 16))       # cf_pm10
        weather += '|s_d2=%d' % (int(data_slice[20] + data_slice[21] + data_slice[22] + data_slice[23], 16))         # pm1
        weather += '|s_d0=%d' % (int(data_slice[24] + data_slice[25] + data_slice[26] + data_slice[27], 16))         # pm2.5
        weather += '|s_d1=%d' % (int(data_slice[28] + data_slice[29] + data_slice[30] + data_slice[31], 16))         # pm10
        weather += '|s_t0=%d' % (int(data_slice[48] + data_slice[49] + data_slice[50] + data_slice[51], 16) / 10)    # Temperature
        weather += '|s_h0=%d' % (int(data_slice[52] + data_slice[53] + data_slice[54] + data_slice[55], 16) / 10)    # Humidity 
        return weather 

def upload_data(msg, pm_s, loc_s):
    if pm_s == 1:
        msg += '|app=%s' % (Conf.APP_ID)
        msg += '|device=%s' % (Conf.DEVICE)
        msg += '|device_id=%s' % (Conf.DEVICE_ID)
        msg += '|tick=%f' % (Conf.tick)
        msg += '|fmt_opt=%d' % (Conf.fmt_opt)
        msg += '|ver_format=%d' % (Conf.ver_format)
        msg += '|gps_fix=%d' % (Conf.gps_fix)
        msg += '|ver_app=%s' % (Conf.ver_app)
        msg += '|FAKE_GPS=%d' % (Conf.FAKE_GPS)
    
        Restful_URL = Conf.Restful_URL
        print(msg)
        restful_str = "wget -O /tmp/last_upload.log \"" + Restful_URL + "device_id=" + Conf.DEVICE_ID + "&msg=" + msg + "\""
        try:
            os.system(restful_str)
        except Exception as e:
            print(e)
    else:
        print("Error: Won't upload data")
 
G5T_GPIO = 23
GPS_GPIO = 24
path = "/home/pi/Data/"

########## Start PIGPIO ##########
status, process = commands.getstatusoutput('sudo pidof pigpiod')

if status:  #  it wasn't running, so start it
    print "pigpiod was not running"
    commands.getstatusoutput('sudo pigpiod')  # start it
    time.sleep(1)
    pi = pigpio.pi()

if not status:  # if it worked, i.e. if it's running...
    pigpiod_process = process
    print "pigpiod is running, process ID is: ", pigpiod_process
    try:
        pi = pigpio.pi()  # local GPIO only
        print "pi is instantiated successfully"
    except Exception as e:
        print "problem instantiating pi, the exception message is: ", e
##################################

while True:
    weather_data = ""
    PM_STATUS = -1    # get pm2.5 data
    LOCATION_STATUS = -1  # get location information

    ########## Read G5T ##########
    try:
        pi.bb_serial_read_close(G5T_GPIO)
    except Exception as e:
        pass

    try:
        pi.bb_serial_read_open(G5T_GPIO, 9600)
        time.sleep(1)
        (G5T_status, G5T_data) = pi.bb_serial_read(G5T_GPIO)
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S").split(" ")
        if G5T_status:
            print("read G5T")
            data_hex = bytes2hex(G5T_data)
            pm_data = G5T_data_read(data_hex)
            if len(pm_data):
                weather_data += pm_data
                PM_STATUS = 1
            weather_data += '|date=%s' % (str(now_time[0]))
            weather_data += '|time=%s' % (str(now_time[1]))
        else:
            print("read nothing")
    except Exception as e:
        print(e)

    try:
        pi.bb_serial_read_close(G5T_GPIO)
        print("G5T close success")
    except Exception as e: 
        pass
    #############################
   
    print("weather_data: ", weather_data)
    print("\n")
    time.sleep(3)

    ########## Read GPS ##########
    try:
        pi.bb_serial_read_close(GPS_GPIO)
    except Exception as e:
        pass
    
    try:
        pi.bb_serial_read_open(GPS_GPIO, 9600)
        time.sleep(1)
        (GPS_status, GPS_data) = pi.bb_serial_read(GPS_GPIO)
        if GPS_status:
            print("read GPS")
            lines = ''.join(chr(x) for x in GPS_data).splitlines()
            loc_data = GPS_data_read(lines)
            if len(loc_data):
                weather_data += loc_data
                LOCATION_STATUS = 1
        else:
            print("read nothing")
    except Exception as e:
        print(e)
    
    try:
        pi.bb_serial_read_close(GPS_GPIO)
        print("GPS close success")
    except Exception as e:
        pass
    ###############################

    print("weather_data: ", weather_data)
    print("\n")
    upload_data(weather_data, PM_STATUS, LOCATION_STATUS)
    time.sleep(3)
    print("\n")

    ########## Store msg ##########
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S").split(" ")
    with open(path + str(date[0]) + ".txt", "a") as f:
        try:
            if len(weather_data):
                f.write(weather_data + "\n")
        except Exception as e:
            print(e)
            print "Error: writing to SD"    
    ##############################
    time.sleep(291)

pi.stop()
print("End")

