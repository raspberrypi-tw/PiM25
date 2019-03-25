import time
import pigpio
import commands
import os
import csv
from datetime import datetime

import lib.GPS_module as GPS_m
import lib.G5T_module as G5T_m
import lib.PiM25_config as Conf
import lib.upload_data as upload
# import lib.screen as lcd

if __name__ == '__main__':

    ## initial PIGPIO library ##
    (s, process) = commands.getstatusoutput('sudo pidof pigpiod')
    if s:  
        print("pigpiod was not running")
        commands.getstatusoutput('sudo pigpiod')
        time.sleep(0.5)
        pi = pigpio.pi()

    if not s:
        print "pigpiod is running, process ID is: ", process
        try:
            pi = pigpio.pi()
        except Exception as e:
            print "initial pi fail, the error message is: ", e
 
    ## collect all sensor data ##
    weather_data = Conf.device_info.copy()

    ## check pm2.5 sensor status ##
    PM_STATUS = -1

    ## check gps sensor status ##
    LOCATION_STATUS = -1

    ## check OLED screen status ##
    SCREEN_STATUS = -1

    ########## Read G5T ##########
    try:
        pi.bb_serial_read_close(Conf.G5T_GPIO)
    except:
        pass

    try:
        pi.bb_serial_read_open(Conf.G5T_GPIO, 9600)
        time.sleep(1)
        (s, raw_data) = pi.bb_serial_read(Conf.G5T_GPIO)
        G5T_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S").split(" ")
        if s:
            print("read G5T")
            data_hex = G5T_m.bytes2hex(raw_data)
            weather_data, check  = G5T_m.data_read(data_hex, weather_data)
            if check is 1:
                ## collect pm2.5 data ##
                PM_STATUS = 1

                ## record sensor time ##
                weather_data["date"] = (str(G5T_time[0]))
                weather_data["time"] = (str(G5T_time[1]))
        else:
            print("read nothing")
            PM_STATUS = -1

    except Exception as e:
        print(e)
        PM_STATUS = -1

    try:
        pi.bb_serial_read_close(G5T_GPIO)
        print("G5T close success")
    except Exception as e: 
        pass
    #############################
   
    # print("weather_data: ", weather_data)

    ########## Read GPS ##########
    try:
        pi.bb_serial_read_close(Conf.GPS_GPIO)
    except Exception as e:
        pass
    
    try:
        pi.bb_serial_read_open(Conf.GPS_GPIO, 9600)
        time.sleep(1)
        (s, raw_data) = pi.bb_serial_read(Conf.GPS_GPIO)
        if s:
            print("read GPS")
            lines = ''.join(chr(x) for x in raw_data).splitlines()
            weather_data = GPS_m.data_read(lines, weather_data)
            LOCATION_STATUS = 1

        else:
            print("read nothing")
            weather_data = GPS_m.read_last_gps(weather_data)
            LOCATION_STATUS = -1

    except Exception as e:
        print(e)
        LOCATION_STATUS = -1
    
    try:
        pi.bb_serial_read_close(GPS_GPIO)
        print("GPS close success")
    except Exception as e:
        pass
    
    ###############################
    
    # print("weather_data: ", weather_data)
    
    ###############################

    weather_data = upload.organize(weather_data, PM_STATUS, LOCATION_STATUS)
    
    ########## Store msg ##########
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S").split(" ")
   
    info_key = weather_data.keys()
    store_data = [weather_data]
    if os.path.exists(Conf.data_path + "record.csv") is False:
        with open(Conf.data_path + "record.csv", "a") as output_file:
            dict_writer = csv.DictWriter(output_file, info_key)
            dict_writer.writeheader()
         
    with open(Conf.data_path + "record.csv", "a") as output_file:
        try:
            dict_writer = csv.DictWriter(output_file, info_key)
            dict_writer.writerows(store_data)
        except Exception as e:
            print(e)
            print("Error: writing to SD")

    ##############################
    
    # lcd.display(weather_data) 
    pi.stop()
    print("End")
