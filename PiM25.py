#!/usr/bin/env python
# -*- coding: utf-8 -*-

# SUGGESTED CONNECTIONS, but you can of course do it differenlty!
##############################################################             
#           Raspberry Pi 3 GPIO Pinout;           Corner --> #
#                    (pin 1)  | (pin 2)                      #                  
#  OLED/GPS Vcc       +3.3V   |  +5.0V    Gas sensor GND     #
#  OLED SDA          GPIO  2  |  +5.0V    PM25 G3 pin 1 Vcc b#     
#  OLED SCL          GPIO  3  |  GND      PM25 G3 pin 2 GND o#
#                    GPIO  4  | UART TX                      #
#  OLED/Gas GND       GND     | UART RX                      #
#                    GPIO 17  | GPIO 18   PM25 G3 pin 5 TX  g#
#                    GPIO 27  |  GND                         #
#                    GPIO 22  | GPIO 23                      #
#r MCP3008 Vcc/Vref   +3.3V   | GPIO 24                      #
#                    GPIO 10  |  GND      DHT22 GND         g#
#                    GPIO  9  | GPIO 25   DHT22 DATA        b#                      #
#                    GPIO 11  | GPIO  8   DHT22 POWER       p#
#                     GND     | GPIO  7                      #
#                    Reserved | Reserved                     #
#                    GPIO  5  |  GND                         #
#b MCP3008 CLK       GPIO  6  | GPIO 12                      #
#g MCP3008 MISO      GPIO 13  |  GND      (GPS GND)          #
#y MCP3008 MOSI      GPIO 19  | GPIO 16   (GPS TX)           #
#o MCP3008 CSbar     GPIO 26  | GPIO 20                      #
#brMCP3008 GND/GND    GND     | GPIO 21                      #
#                   (pin 39)  | (pin 40)                     #                  
##############################################################


import pigpio, smbus
import atexit 
import re, commands
import psutil        # http://psutil.readthedocs.io/en/latest/

import yaml

import time, datetime
import numpy as np
import paho.mqtt.client as mqtt
import json

from binascii import hexlify
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt

import logging    # heyhere

class BOX(object):

    devkind = "BOX"

    def __init__(self, name, use_WiFi=False, use_SMBus=False,
                 use_pigpio=False):

        self.name = name

        # Create and configure logger
        LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s" 
        logging.basicConfig(filename = "PiM25box_logging.log", 
                            level    = logging.DEBUG, 
                            format   = LOG_FORMAT, 
                            filemode = 'w')

        self.logger = logging.getLogger() 

        self.logger.info("box '{}' __init__".format(self.name))  

        self.instance_things = locals()
        donts = ('self', 'name')
        for dont in donts:
            try:
                self.instance_things.pop(dont)
            except:
                pass

        self.name         = name
        self.use_WiFi     = use_WiFi
        self.use_SMBus    = use_SMBus
        self.use_pigpio   = use_pigpio

        self.devices      = []
        self.LOG_devices  = [] 
        self.LASS_devices = [] 

        self.mac_address    = None
        self.get_mac_address()

        if self.use_WiFi:
            self._get_nWiFi()
            self.WiFi_setstatus('on')
            self.logger.info("WiFi_setstatus('on')") 
        else:
            pass

        print '    testing self.use_pigpio: ', self.use_pigpio
        if self.use_pigpio:
            print '    it was True'
            self.make_a_pi()
            self.logger.info("make_a_pi()") 
        else:
            print '    it was False'
            self.pi              = None
            self.pigpiod_process = None

        if self.use_SMBus:
            self.bus             = smbus.SMBus(1)
            self.logger.info("smbus.SMBus(1)")
        else:
            self.bus             = None

    def __repr__(self):
        return ('{self.__class__.__name__}({self.name})'
                .format(self=self))

    def clear_all_device_datadicts(self):
        for device in self.devices:
            device.datadict = dict()    # easiest way to clear!

    def read_all_devices(self):
        for device in self.devices:
            device.read()               # each device repopulates its datadict

    def get_system_timedate_dict(self):

        sysnow              = datetime.datetime.now()
        sysnow_str          = sysnow.strftime("%Y-%m-%d %H:%M:%S")
        sysdate_str         = sysnow_str[:10]
        systime_str         = sysnow_str[11:]
        sysmicroseconds_str = str(sysnow.microsecond)
        
        systimedatedict     = dict()

        systimedatedict['sysnow_str'] = sysnow_str
        systimedatedict['timestr']    = systime_str
        systimedatedict['datestr']    = sysdate_str
        systimedatedict['tickstr']    = sysmicroseconds_str

        return systimedatedict

    def make_a_pi(self):

        status, process = commands.getstatusoutput('sudo pidof pigpiod')   # check it

        if status:  #  it wasn't running, so start it
            print "pigpiod was not running"
            self.logger.info("pigpiod was not running") 
            commands.getstatusoutput('sudo pigpiod')  # start it
            time.sleep(0.5)
            status, process = commands.getstatusoutput('sudo pidof pigpiod')   # check it again        

        if not status:  # if it worked, i.e. if it's running...
            self.pigpiod_process = process
            print "pigpiod is running, process ID is: ", self.pigpiod_process
            self.logger.info("pigpiod is running, process ID is: {}".format(self.pigpiod_process))

            try:
                self.pi = pigpio.pi()  # local GPIO only
                print "pi is instantiated successfully"
                self.logger.info("pi is instantiated successfully")
            except Exception, e:
                str_e = str(e)
                print "problem instantiating pi, the exception message is: ", str_e
                self.logger.warning("problem instantiating pi: {}".format(str_e))
                self.start_pigpiod_exception = str_e

    # METHODS that involve WiFi

    def WiFi_setstatus(self, on_or_off):
        if type(on_or_off) is str:
            if on_or_off.lower() == 'on':
                self.WiFi_on()
            elif on_or_off.lower() == 'off':
                self.WiFi_off()
            else:
                print "WiFi_onoff unrecognized string"
                self.logger.warning("WiFi_onoff unrecognized string: {}".format(on_or_off))
        else:
            if on_or_off:
                self.WiFi_on()
            else:
                self.WiFi_off()

    def get_WiFi_is_on(self):
        WiFi_is_on = None
        try:
            stat, isblocked = commands.getstatusoutput("sudo rfkill list " +
                                                       str(self.nWiFi) +
                                                       " | grep Soft | awk '{print $3}'")
            if isblocked == 'yes':
                WiFi_is_on = False
                print "WiFi is off"
                self.logger.info("WiFi is off")
            elif isblocked == 'no':
                WiFi_is_on = True
                print "WiFi is on" 
                self.logger.info("WiFi is on")
            else:
                print "can't tell if WiFi is on or off"
        except:
            print "problem checking WiFi status"
            self.logger.warning("problem checking WiFi status") 

        return WiFi_is_on

    def WiFi_on(self):
        stat, out = commands.getstatusoutput("sudo rfkill unblock " + str(self.nWiFi))
        if stat:
            print "problem turning WiFi on" , stat, out       
            self.logger.warning("problem turning WiFi on") 

    def WiFi_off(self):
        
        stat, out = commands.getstatusoutput("sudo rfkill block " + str(self.nWiFi))
        if stat:
            print "problem turning WiFi off"
            self.logger.warning("problem turning WiFi off") 

    def _get_nWiFi(self):

        stat, out = commands.getstatusoutput("sudo rfkill list | grep phy0 | awk '{print $1}'")
        try:
            self.nWiFi = int(out.replace(':', '')) # confirm by checking that it can be an integer
            self.logger.info("nWiFi: {}".format(self.nWiFi))  # heyhere
        except:
            # print "there was an exception! "
            self.logger.warning("there was a problem checking nWiFi!")  # heyhere
            self.nWiFi = None

    # METHODS that involve ntpdate

    def _do_ntpdate(self):
        stat, out = commands.getstatusoutput("sudo ntpdate")
        # needs work!
        return stat, out

    # METHODS that involve MAC address

    def get_mac_address(self):

        # https://stackoverflow.com/questions/159137/getting-mac-address
        # Nice: https://forums.hak5.org/topic/20372-python-script-to-get-mac-address/
        # Wow! https://stackoverflow.com/questions/24196932/how-can-i-get-the-ip-address-of-eth0-in-python
        # also https://stackoverflow.com/questions/159137/getting-mac-address

        ifconfig = commands.getoutput("ifconfig eth0 " +
                                      " | grep HWaddr | " + 
                                      "awk '{print $5}'")
        # print ' ifconfig: ', ifconfig
        self.logger.info("ifconfig: {}".format(ifconfig)) 
  
        if type(ifconfig) is str:
            possible_mac = ifconfig.replace(':','')   # alternate
            if len(possible_mac) == 12:
                self.mac_address = possible_mac
                self.logger.info("self.mac_address: {}".format(possible_mac))

    # METHODS that involve system status

    def _get_some_system_info_lines(self):
        info_lines = ['', '--------', '--------']
        things     = ('uname -a', 'lsb_release -a', 'df -h', 'free',
                     'vcgencmd measure_temp')
        for thing in things:
            err, msg = commands.getstatusoutput(thing)
            if not err:
                info_lines += ['COMMAND: ' + thing +
                               ' returns: ' + msg, '--------']
            else:
                info_lines += ['COMMAND: ' + thing +
                               ' returns: error', '--------']
        info_lines += ['--------']
        
        return info_lines

    def print_some_system_info_lines(self):
        info_lines = _get_some_system_info_lines()
        for line in info_lines:
            print line
     

    def get_system_datetime(self):

        sysnow              = datetime.datetime.now()
        sysnow_str          = sysnow.strftime("%Y-%m-%d %H:%M:%S")
        sysdate_str         = sysnow_str[:10]
        systime_str         = sysnow_str[11:]
        sysmicroseconds_str = str(sysnow.microsecond)

        return sysnow_str

    def show_CPU_temp(self):
        temp = None
        err, msg = commands.getstatusoutput('vcgencmd measure_temp')
        #if not err:
            #m = re.search(r'-?\d+\.?\d*', msg)
            #try:
                #temp = float(m.group())
            #except:
                #pass
        # return temp
        return msg    
    
    def add_device(self, device):
        if type(device.name) is not str:
            print "device not added, type(device.name) is not str: {}".format(device.name)
            self.logger.error("device not added, type(device.name) is not str: {}".format(device.name))  # heyhere
        elif len(device.name) == 0:
            print "device not added, zero-length name not allowed"
            self.logger.error("device not added, zero-length name not allowed")  # heyhere
        elif self.get_device(device.name) is not None:
            print "device with name '{}' not added, that name is already present".format(device.name)
            self.logger.error("device with name '{}' not added, that name is already present".format(device.name))  # heyhere
        else:
            self.devices.append(device)
            print "device with unique name '{}' successfully added".format(device.name)
            self.logger.info("device with unique name '{}' successfully added".format(device.name))  # heyhere
        
        
    def new_G3bb(self, name, DATA=None, collect_time=None):
        g3 = G3bb(box=self, name=name, DATA=DATA, collect_time=collect_time)
        self.logger.info("new_G3bb: '{}'".format(g3.name))
        return g3

    def new_GPSbb(self, name, DATA=None, collect_time=None):
        gps = GPSbb(box=self, name=name, DATA=DATA, collect_time=collect_time)
        self.logger.info("new_GPSbb: '{}'".format(gps.name))
        return gps

    def new_DHT22bb(self, name, DATA=None, POWER=None):
        dht = DHT22bb(box=self, name=name, DATA=DATA, POWER=POWER)
        self.logger.info("new_DHT22bb: '{}'".format(dht.name))
        return dht
        
    def new_MCP3008bb(self, name, CSbar=None, MISO=None,
                         MOSI=None, SCLK=None, Vref=None):

        mcp3008 = MCP3008bb(box=self, name=name, CSbar=CSbar,
                               MISO=MISO, MOSI=MOSI, SCLK=SCLK, Vref=Vref)
        self.logger.info("new_MCP3008bb: '{}'".format(mcp3008.name)) 
        return mcp3008

    def new_MOS_gas_sensor(self, name, ADC=None, channel=None,
                           Rseries=None, Calibrationdata=None,
                           use_loglog=None, gasname=None,
                           atlimitsisokay=None):

        gas_sensor = MOS_gas_sensor(box=self, name=name, 
                                    ADC=ADC, channel=channel, Rseries=Rseries,
                                    Calibrationdata=Calibrationdata,
                                    use_loglog=use_loglog, gasname=gasname,
                                    atlimitsisokay=atlimitsisokay)
        self.logger.info("new_MOS_gas_sensor: '{}'".format(gas_sensor.name))
        return gas_sensor
        
    def new_OLEDi2c(self, name):
        oled = OLEDi2c(box=self, name=name)
        self.logger.info("new_OLEDi2c: '{}'".format(oled.name))
        return oled

    def new_Dummy(self, name, dummydatadict=None):
        dummy = Dummy(box=self, name=name, dummydatadict=dummydatadict)
        self.logger.info("new_Dummy: '{}'".format(dummy.name)) 
        return dummy

    def get_device(self, devname):

        try:
            device = [d for d in self.devices if d.name == devname][0]
        except:
            device = None
            
        return device
        
    def new_LASS(self, name=None):
        """wrapper to make instantiation 'look nicer'"""
        lass = LASS(self, name)
        self.LASS_devices.append(lass)
        self.logger.info("new_LASS: '{}'".format(lass.name)) 
        return lass

    def new_LOG(self, filename='deleteme.txt', name=None):
        """wrapper to make instantiation 'look nicer'"""
        log = LOG(self, filename, name)
        self.logger.info("new_LOG: '{}' filename: '{}'".format(log.name, log.filename)) 
        return log


class LASS(object):
    def __init__(self, box, name=None):

        self.box              = box
        self.name             = name
        self.devkind          = 'LASS'

        self.box.logger.info("LASS '{}' __init__".format(self.name))  

        self.mac_address      = box.mac_address
        
        self.last_system_info = None    # double check this should be here
        
        self.devices          = []

        # six static box
        self.app              = 'PiM25'
        self.ver_app          = '0.1.0'
        self.device           = 'PiM25Box ' + name
        self.device_id        = None # replace with MAC yes mac YES mac yes!
        self.ver_format       = 3 # what does this mean?   always 3
        self.fmt_opt          = 1 # (0) default (real GPS) (1) gps information invalid   always 0 or 1

        self.battery_level_static    = 100.0
        self.battery_mode_static     = 1.0
        self.motion_speed_static     = 0.0
        self.CPU_utilization_static  = 0.0  # Hey link this up

        self.sequence_number         = 1 

        self.static_lat       = None
        self.static_lon       = None
        self.static_alt       = None
        self.static_fix       = 0
        self.static_num       = 0

        # MQTT
        self.client = mqtt.Client()
        self.host = 'gpssensor.ddns.net'
        self.topic = 'LASS/Test/PM25'
        self.client.connect(self.host, 1883, 60)


    def __repr__(self):
        return ('{self.__class__.__name__}({self.name})'
                .format(self=self))

    def set_static_location(self, latlon=tuple, alt=None):

        self.static_latlon = latlon
        self.static_alt    = alt
        if type(latlon) == tuple and len(latlon) >= 2:
            if all([type(x) in (float, int) for x in latlon[:2]]):
                self.static_lat = latlon[0]
                self.static_lon = latlon[1]
                print "static latitude and longitude set."
                self.box.logger.info("set static latitude: {} longitude: {}"
                                     .format(self.static_lat, self.static_lon))
            elif all([type(x) is str for x in latlon[:2]]):
                try:
                    lat, lon = [float(x) for x in latlon[:2]]
                    self.static_lat = lat
                    self.static_lon = lon
                    print "static latitude and longitude set."
                    self.box.logger.info("set static latitude: {} longitude: {}"
                                         .format(self.static_lat, self.static_lon)) 
                except:
                    print "static latitude and longitude set has failed!"
                    self.box.logger.error("static latitude and longitude set has failed!") 
                    pass

        if type(alt) is float:
            self.static_alt = alt
            print "static altitude set."
            self.box.logger.info("sstatic altitude set: {}".format(self.static_alt)) 
        
    def set_sources(self, humsrc=None, tempsrc=None, pm25src=None,
                    pm1src=None, pm10src=None, timedatesrc=None,
                    GPSsrc=None, gassensors=None):

        self.source_dict = dict()
        
        self._lookup = {'humidity':{'DHT22':'s_h0', 'HTS221':'s_h1', 'SHT31':'s_h2',
                              'HTU21D':'s_h3', 'BME280':'s_h4', 'SHT25':'s_h5',
                              'other':'s_h9'}, 
                  'temperature':{'DHT22':'s_t0', 'HTS221':'s_t1', 'SHT31':'s_t2',
                              'HTU21D':'s_t3', 'BME280':'s_t4', 'SHT25':'s_t5',
                              'other':'s_t9'},
                  'PM25':{'G3':'s_d0', 'Panasonic':'s_d3', 'other':'s_d7'},
                  'PM1' :{'G3':'s_d1', 'other':'s_d8'},
                  'PM10':{'G3':'s_d2', 'other':'s_d9'}}

        self._gaslookup = {'NH3':'s_g0', 'CO':'s_g1', 'NO2':'s_g2', 'C3H8':'s_g3',
                     'C4H10':'s_g4', 'CH4':'s_g5', 'H2':'s_g6',
                     'C2H5OH':'s_g7', 'CO2':'s_g8', 'TVOC':'s_gg'}

        if humsrc:
            param, source = 'humidity',    humsrc
            self.source_dict[self._lookup[param][source.devkind]] = (source, param)
            self.box.logger.info("LASS {}: humsrc: {} param: {}"
                                 .format(self.name, source, param)) 

        if tempsrc:
            param, source = 'temperature', tempsrc
            self.source_dict[self._lookup[param][source.devkind]] = (source, param)
            self.box.logger.info("LASS {}: tempsrc: {} param: {}"
                                 .format(self.name, source, param)) 
       
        if pm25src:
            param, source = 'PM25',        pm25src
            self.source_dict[self._lookup[param][source.devkind]] = (source, param)
            self.box.logger.info("LASS {}: pm25src: {} param: {}"
                                 .format(self.name, source, param)) 
             
        if pm1src:
            param, source = 'PM1',        pm1src
            self.source_dict[self._lookup[param][source.devkind]] = (source, param)
            self.box.logger.info("LASS {}: pm1src: {} param: {}"
                                 .format(self.name, source, param)) 
       
        if pm10src:
            param, source = 'PM10',        pm10src
            self.source_dict[self._lookup[param][source.devkind]] = (source, param)
            self.box.logger.info("LASS {}: pm10src: {} param: {}"
                                 .format(self.name, source, param)) 

        if not gassensors:
            gassensors = []

        for sensor in gassensors:
            param, source, gasname = 'ppm', sensor, sensor.devkind
            self.source_dict[self._gaslookup[gasname]] = (source, param)
            self.box.logger.info("LASS {}: gas sensor: {} param: {}, gasname: {}"
                                 .format(self.name, source, param, gasname)) 

        if type(GPSsrc) is str and GPSsrc.lower() == 'static':
            self.source_dict['gps_lat'] = ('static', 'static_lat')
            self.source_dict['gps_lon'] = ('static', 'static_lon')
            self.source_dict['gps_alt'] = ('static', 'static_alt')
            self.source_dict['gps_fix'] = ('static', 'static_fix')
            self.source_dict['gps_num'] = ('static', 'static_num')
            self.fmt_opt           = 1 # (0) default (real GPS) (1) gps information invalid   always 0 or 1
            self.box.logger.info("LASS {}: GPSsrc: {}:"
                                 .format(self.name, 'static'))
            
        else:
            self.source_dict['gps_lat'] = (GPSsrc,   'latitude' )
            self.source_dict['gps_lon'] = (GPSsrc,   'longitude')
            self.source_dict['gps_alt'] = (GPSsrc,   'altitude' )
            self.source_dict['gps_fix'] = (GPSsrc,   'fix'      )
            self.source_dict['gps_num'] = (GPSsrc,   'satnum'   )
            self.source_dict['gps_num'] = (GPSsrc,   'satnum'   )
            self.fmt_opt           = 0 # (0) default (real GPS) (1) gps information invalid   always 0 or 1
            self.box.logger.info("LASS {}: GPSsrc: {}:"
                                 .format(self.name, GPSsrc))

        if type(timedatesrc) is str and timedatesrc.lower() == 'system':
            self.source_dict['time']  = ('system',  'timestr')
            self.source_dict['date']  = ('system',  'datestr')
            self.source_dict['ticks'] = ('system',  'tickstr')
            self.box.logger.info("LASS {}: timedatesrc: {}:"
                                 .format(self.name, 'system'))
        else:
            self.source_dict['time']  = (timedatesrc, 'timestr')
            self.source_dict['date']  = (timedatesrc, 'datestr')
            self.source_dict['ticks'] = ('system',    'tickstr')
            self.box.logger.info("LASS {}: timedatesrc: {}:"
                                 .format(self.name, timedatesrc))

        # 's_gx' g0,  g1, g2,  g3,   g4,    g5,  g6  g7,     g8,              gg
        # 's_gx' NH3, CO, NO2, C3H8, C4H10, CH4, H2, C2H5OH, SenseAir S8 CO2, TVOC
        # 's_hx' h0,    h1,     h2,    h3,     h4,     h5,
        # 's_hx' DHT22, HTS221, SHT31, HTU21D, BME280, SHT25
        # 's_tx' s_t0,   s_t1,  s_t2,   s_t3,   s_t4,   s_t5
        # 's_tx' DHT22, HTS221, SHT31, HTU21D, BME280, SHT25
        # 's_dx' d0,    d1,   d2   d3
        # 's_dx' PM2.5, PM10, PM1, Panasonic

    def build_entry(self):

        self.LASS_data = []

        # static box information
        self.LASS_data.append('ver_format=' + str(self.ver_format))
        self.LASS_data.append('fmt_opt='    + str(self.fmt_opt))
        self.LASS_data.append('app='        + str(self.app))
        self.LASS_data.append('ver_app='    + str(self.ver_app))
        self.LASS_data.append('device_id='  + str(self.device_id))
        self.LASS_data.append('device='     + str(self.device))

        systdd = self.box.get_system_timedate_dict()
              
        for key, (source, param) in self.source_dict.items():
            if (key in ('time', 'date', 'ticks') and source == 'system'):
                thing = systdd[param]
                if type(thing) is str and len(thing) >=8:
                    self.LASS_data.append(key  + '=' + systdd[param])
            elif ('gps' in key and source == 'static'):
                thing = getattr(self, param)
                if thing != None:
                    self.LASS_data.append(key  + '=' + str(thing) )
            else:
                try:
                    thing = source.datadict[param]
                    if thing != None:
                        self.LASS_data.append(key  + '=' + str(thing))
                except:
                    pass
                           
        # https://www.saltycrane.com/blog/2008/11/python-datetime-time-conversions/
        
        # sequence number
        self.LASS_data.append('s_0=' + str(self.sequence_number))
        self.sequence_number += 1

        # battery level 
        self.LASS_data.append('s_1=' + str(self.battery_level_static))

        # battery mode
        self.LASS_data.append('s_2=' + str(self.battery_mode_static))

        # motion speed 
        self.LASS_data.append('s_3=' + str(self.motion_speed_static))

        # CPU utilization
        # http://psutil.readthedocs.io/en/latest/
        self.CPU_utilization = psutil.cpu_percent()
        self.LASS_data.append('s_4=' + str(self.CPU_utilization))

        self._generate_LASS_string() 
        self.send_to_LASS()

    def _generate_LASS_string(self):
        self.LASS_string =  '|'.join([''] + self.LASS_data + [''])
        self.box.logger.info("LASS_string '{}'".format(self.LASS_string))  
        return self.LASS_string 

    def send_to_LASS(self):
        print "=============================="
        print time.ctime(), self.LASS_string
        self.box.logger.info("send_to_LASS: {}".format(self.LASS_string))
        self.client.publish(self.topic, "%s" % ( self.LASS_string ))
        print "=============================="
        # return self.LASS_string


    def build_and_send_to_LASS(self):
        self.build_entry()
        self.send_to_LASS()
        return self.LASS_string

        # ['ver_format', 'fmt_opt', 'app', 'ver_app', 'device_id', 'tick',
        # 'date', 'time', 'device', 's_0', 's_1', 's_2', 's_3', 's_d0',
        # 's_t0', 's_h0', 'gps_lat', 'gps_lon', 'gps_fix', 'gps_num',
        # 'gps_alt']

        # time hh:mm:ss
        # date yyyy-mm-dd

        # 's_0' # sequence number
        # 's_1' # battery level
        # 's_2' # battery mode vs charging
        # 's_3' # motion speed
        # 's_4' # CPU utiliation
        
        # 's_bx' # barometer b0, b1, b2 = Grove, BMP180, BME280
        # 's_dx' # dust  d0, d1, d2 is PM2.5, PM10, PM1, d3 Panasonic
        # 's_gx' # gas g0, g1, g2, g3, g4, g5, g6 g7, g8, gg
        # 's_gx' # gas NH3, CO, NO2, C3H8, C4H10, CH4, H2, C2H5OH, SenseAir S8 CO2, TVOC
        # 's_hx' # h0, h1, h2, h3, h4, h5, DHT22, HTS221, SHT31, HTU21D, BME280, SHT25

        # 's_Ix' # light
        # 's_nx' # radiation
        # 's_ox' # other, misc
        # 's_px' # rain
        # 's_sx' # sound
        # 's_tx' # temperature, t0, t1, t2, t3, t4, t5 is DHT22, HTS221, SHT31, HTU21D, BME280, SHT25
        # 's_wx' # winds w0, w1 speed, direction
        # 's_rx' # rainfall r10, r60 is 10 and 60 minutes


class LOG(object):

    def __init__(self, box, filename, name=None):
        
        self.box                = box
        self.name               = name
        self.filename           = filename 
        self.devices            = []

        self.box.logger.info("LOG '{}' __init__ logfilename: '{}'"
                             .format(self.name, self.filename))

        self.t_previous_sysinfo = None

        headerlines = []
        headerlines.append('New log file, filename = ' + str(self.filename))
        headerlines.append('New log file, log name = ' + str(self.name))

        datetimedict = self.box.get_system_timedate_dict()

        headerlines.append('Time = ' + datetimedict['timestr'])
        headerlines.append('Date = ' + datetimedict['datestr'])
        headerlines.append('box name = ' + str(self.box.name))
        try:
            headerlines.append('box MAC address = ' +
                               str(self.box.macaddress))
        except:
            pass

        with open(filename, 'w') as outfile:
            outfile.writelines([line + '\n' for line in headerlines])
            
    def __repr__(self):
        return ('{self.__class__.__name__}({self.name})'
                .format(self=self))

    def configure(self, logconfigure_dict):

        for device, datakeys in logconfigure_dict.items():
            if device in self.box.devices:
                self.devices.append((device, datakeys))
                # does not test if datakeys are there, device may be flexible.
            else:
                print "Not added. This is not in box.devices"

    def build_entry(self, sysinfo_interval=None):
        
        self.datadict = dict()
        
        self.datadict['buildtime'] = self.box.get_system_datetime()

        try:
            time_since = time.time() - self.t_previous_sysinfo
        except:
            time_since = None

        if ((time_since == None) or
            (time_since > sysinfo_interval) or
            (sysinfo_interval<=0)):

            sysinfolines = self.box._get_some_system_info_lines()

            self.datadict['sysinfolines'] = sysinfolines

            self.t_previous_sysinfo = time.time()

        for device, datakeys in self.devices:

            devdict = dict()

            self.datadict[device.name] = devdict

            for dk in datakeys:

                try:
                    devdict[dk] = device.datadict[dk]
                except:
                    pass

    def save_entry(self):

        lines = []
        try:
            lines += self.datadict.pop('sysinfolines')
        except:
            pass
        for key, info in self.datadict.items():
            lines += [key]
            if type(info) is list:
                lines += info
            elif type(info) is str:
                lines += [info]
            elif type(info) is dict:
                for datakey, data in info.items():
                    lines += ['  datakey: ' + datakey + ' = ' + str(data)]

        with open(self.filename, 'a') as outfile:   # note, append!!!
            outfile.writelines([line + '\n' for line in lines])
                
        self.log_entry_lines = lines   # save for debugging

    def build_and_save_entry(self, sysinfo_interval=None):

        self.build_entry(sysinfo_interval=sysinfo_interval)
        self.save_entry()
        

class GPIO_DEVICE(object):

    def __init__(self, box, name=None):

        self.box              = box
        self.pi               = self.box.pi
        self.bus              = self.box.bus
        self.name             = name
        self.datadict         = dict()
        self.statistics       = {'nreads':0, 'ngoodreads':0, 
                                 'nbadreads':0} # minimal each may have more
        self.last_twenty_stats = []

        self.box.add_device(self)

        donts = ('self', 'name', 'box')
        for dont in donts:
            try:
                self.instance_things.pop(dont)
            except:
                pass

    def __repr__(self):
                return ('{self.__class__.__name__}({self.name})'
                        .format(self=self))

    def get_my_current_instance_info(self):

        current_info = dict()
        for key in self.instance_things:
            current_info[key] = getattr(self, key)
        return current_info

    def get_my_original_instance_info(self):

        original_info = self.instance_things.copy()

        return original_info

    def _last_twenty_increment(self): 

        self.last_twenty_stats = ([self.last_read_is_good] +
                                  self.last_twenty_stats[:19])


class Dummy(GPIO_DEVICE):

    devkind       = 'Dummy'

    def __init__(self, box, name, dummydatadict=None):

        self.instance_things = locals()

        GPIO_DEVICE.__init__(self, box, name)

        self.box.logger.info("Dummy '{}' __init__".format(self.name))  

        if type(dummydatadict) == dict:
            self.datadict.update(dummydatadict)

    def read(self): # doesn't really read anything

        self.last_read_is_good                = False
        self.statistics['nreads']            += 1 

        self.datadict['read_time']            = time.time()

        self.last_read_is_good                = True # it's a dummy!       
        if self.last_read_is_good:
            self.statistics['ngoodreads']    += 1 
        else: 
            self.statistics['nbadreads']     += 1 

        self._last_twenty_increment()


class G3bb(GPIO_DEVICE):

    devkind = "G3"

    def __init__(self, box, name, DATA, collect_time=None):

        self.instance_things = locals()

        GPIO_DEVICE.__init__(self, box, name)

        self.box.logger.info("G3bb '{}' __init__".format(self.name))  

        if collect_time == None:
            collect_time      = 3.0

        self.collect_time     = collect_time
        self.DATA             = DATA
        self.baud             = 9600
        self.key              = '424d'

    def read(self):

        self.datadict = dict()    # assures the old dict has been cleared.

        self.last_read_is_good            = False
        self.statistics['nreads']        += 1

        try:
            self.pi.bb_serial_read_close(self.DATA)
        except:
            pass

        self.pi.bb_serial_read_open(self.DATA, self.baud) 
        time.sleep(self.collect_time)

        self.datadict['start_read_time'] = time.time()

        size, data = self.pi.bb_serial_read(self.DATA)
        data_hexlified = hexlify(data)

        self.datadict['size']            = size
        self.datadict['data_hexlified']  = data_hexlified
        self.datadict['read_time']       = time.time()

        # For G3, just look at the section of data between any two
        # occurences of the key (n1, n2)

        if size >= 32:
            dn = 1
            n1 = data_hexlified[0    :].find(self.key)
            n2 = data_hexlified[n1+dn:].find(self.key)

            self.datadict['dn']       = dn
            self.datadict['n1']       = n1
            self.datadict['n2']       = n2

            if n2 + dn - n1 == 64:

                six_ints = [int(data_hexlified[2*i:2*(i+1)], 16) for i in range(4, 10)]

                self.datadict['six_ints'] = six_ints

                if len(six_ints) == 6:
                    three = [256*a + b for a, b in zip(six_ints[0::2], six_ints[1::2])]
                    self.datadict['three']    = three    # for debugging 
                    PM1, PM25, PM10 = three
                    self.datadict['PM1']      = PM1
                    self.datadict['PM25']     = PM25
                    self.datadict['PM10']     = PM10
                    self.last_read_is_good    = True        

        if self.last_read_is_good:
            self.statistics['ngoodreads']    += 1 
        else: 
            self.statistics['nbadreads']     += 1 

        self._last_twenty_increment() 
                    

class GPSbb(GPIO_DEVICE):

    devkind = "GPS"   # "u-blox NEO 6, 7" 

    def __init__(self, box, name, DATA, collect_time=None):

        self.instance_things = locals()

        GPIO_DEVICE.__init__(self, box, name)

        self.box.logger.info("GPSbb '{}' __init__".format(self.name))  

        if collect_time == None:
            collect_time = 3.0

        self.DATA  = DATA

        # okdict          = {'GNGGA':15, 'GNRMC':13, 'GNGLL':8}
        # latlonstartdict = {'GNGGA':2, ' GNRMC':3,  'GNGLL':1}
        # timestartdict   = {'GNGGA':1, ' GNRMC':1,  'GNGLL':5}

        self.sentence_type         = "$GNGGA"
        self.ok_length             = 15
        self.speed_sentence_type   = "$GNVTG"   #  speed
        self.speed_ok_length       = 10
        self.satpos_sentence_type  = "$GPGSV"   #  satellite positions

        self.DATA        = DATA
        self.baud             = 9600
        
        if collect_time  == None:
            collect_time = 3.
        self.collect_time     = collect_time

    def _read_chunk(self):
                            
        try:
            self.status = self.pi.bb_serial_read_close(self.DATA)
        except:
            self.status = None
            pass

        self.status  = self.pi.bb_serial_read_open(self.DATA, self.baud)

        time.sleep(self.collect_time)

        size, data   = self.pi.bb_serial_read(self.DATA)
        lines        = ''.join([chr(x) for x in data]).splitlines()

        self.status  = self.pi.bb_serial_read_close(self.DATA)

        return lines

    def _get_degs(self, string, hemisphere):

        A, B    = string.split('.')

        mins    = float(A[-2:]) + float('0.' + B)
        degs    = float(A[:-2])

        degrees = degs + mins/60.

        if hemisphere in ('S', 'W'):
            degrees *= -1.

        return degrees        

    def read(self):

        self.datadict = dict()    # assures the old dict has been cleared.

        self.last_read_is_good                = False
        self.statistics['nreads']            += 1 

        self.datadict['start_read_time']      = time.time()
        all_lines                             = self._read_chunk()
        self.datadict['stop_read_time']       = time.time()
        
        n_all_lines    = len(all_lines)
        split_lines    = [line.split(',') for line in all_lines]

        coor_lines     = [line for line in split_lines if
                         (line[0] == self.sentence_type and
                          len(line) == self.ok_length) ]
        
        n_coor_lines   = len(coor_lines)

        speed_lines    = [line for line in split_lines if
                         (line[0] == self.speed_sentence_type and 
                          len(line) == self.speed_ok_length)]

        n_speed_lines  = len(speed_lines)

        satpos_lines   = [line for line in split_lines if
                          line[0] == self.satpos_sentence_type]

        n_satpos_lines = len(satpos_lines)

        self.datadict['n_all_lines']    = n_all_lines
        self.datadict['n_coor_lines']   = n_coor_lines
        self.datadict['n_speed_lines']  = n_speed_lines
        self.datadict['n_satpos_lines'] = n_satpos_lines

        self.datadict['all_lines']      = all_lines
        self.datadict['split_lines']    = split_lines
        self.datadict['coor_lines']     = coor_lines
        self.datadict['speed_lines']    = speed_lines
        self.datadict['satpos_lines']   = satpos_lines

        for line in coor_lines:
            coor_time_string                           = line[1]   # there is no date
            lat_thing, lat_hemi, lon_thing, lon_hemi   = line[2:6]
            fix, n_sats, horiz_dilu                    = line[6:9]
            alti_num, alti_unit, h_geoid, h_geoid_unit = line[9:13]
            empty, checksum                            = line[13:15]

            if bool(fix) and int(n_sats) > 3:

                lat = self._get_degs(lat_thing, lat_hemi)
                lon = self._get_degs(lon_thing, lon_hemi)

                self.datadict['latitude']          = lat
                self.datadict['longitude']         = lon
                self.datadict['fix']               = fix
                self.datadict['n_sats']            = n_sats
                self.datadict['coor_time_string']  = coor_time_string
                self.last_read_is_good             = True        

                if alti_unit.lower() == 'm':
                    self.datadict['altitude_meters'] = alti_num
                else:
                    self.datadict['altitude_meters'] = None

                self.datadict['altitude']       = alti_num
                self.datadict['altitude_units'] = alti_unit

                if h_geoid_unit.lower() == 'm':
                    self.datadict['h_geoid_meters']  = h_geoid
                else:
                    self.datadict['h_geoid_meters']  = None

                self.datadict['h_geoid']        = h_geoid
                self.datadict['h_geoid_units']  = h_geoid_unit

        if self.last_read_is_good:
            self.statistics['ngoodreads']      += 1 
        else: 
            self.statistics['nbadreads']       += 1 

        self._last_twenty_increment()

        # continue with non-critical, additional processing 
        for line in speed_lines:
            speed, speed_units   = line[7:9]

            if speed_units.lower() == 'k':
                self.datadict['speed_kph']         = speed
            else:
                self.datadict['speed_kph']         = None
        
            self.datadict['speed']         = speed
            self.datadict['speed_units']   = speed_units

            speed, speed_units   = line[7:9]                          

        satdict = dict()   # clear old satdict
        for line in satpos_lines:

            line = [x.split('*')[0] for x in line]
            info = [line[4*i:4*(i+1)] for i in range(1, 5)]
            for thing in info:
                try:
                    satdict[thing[0]] = tuple(thing[1:])
                except:
                    pass

        self.datadict['satdict']   = satdict  # very inclusive!


class DHT22bb(GPIO_DEVICE):

    devkind = "DHT22"

    def __init__(self, box, name=None, DATA=None, POWER=None):

        self.instance_things = locals()

        GPIO_DEVICE.__init__(self, box, name)

        self.box.logger.info("DHT22bb '{}' __init__".format(self.name))  

        self.DATA  = DATA
        self.POWER = POWER

        # Following based on https://github.com/joan2937/pigpio/blob/master/EXAMPLES/Python/DHT22_AM2302_SENSOR/DHT22.py

        self.diffs            = []        # time differences (tics = microseconds)

        self.pi.write(self.POWER, 1) # it takes about 2 seconds to activate, should sleep
        
        atexit.register(self.cancel)      # Cancel watchdog on exit

        self.high_tick       =  0
        self.bit             = 40
        self.tick_threshold  = 50        # data is 1 or 0 

        self.pi.set_pull_up_down(self.DATA, pigpio.PUD_OFF)   

        self.pi.set_watchdog(self.DATA, 0)  # Kill any existing watchdogs on the pin

        # Set the callback on the pin now, You'll start the watchdog later
        self.cb = self.pi.callback(self.DATA, pigpio.EITHER_EDGE, 
                                   self._cb2)  

    def _cb2(self, gpio, level, tick):

        diff = pigpio.tickDiff(self.high_tick, tick)

        if level == 0:

            self.diffs.append(diff)

            if self.bit >= 40: # Message complete.
                self.bit = 40

            elif self.bit == 39:  # 40th bit received.
                
                self.pi.set_watchdog(self.DATA, 0)  # deactivate watchdog

            self.bit += 1

        elif level == 1:
            
            self.high_tick = tick
            
            if diff > 250000:
                
                self.bit = -2

        else: # level == pigpio.TIMEOUT:
            
            self.pi.set_watchdog(self.DATA, 0)    # deactivate watchdog

    def read(self):

        self.last_read_is_good                 = False
        self.statistics['nreads']             += 1 

        self.datadict = dict()     # clear old data
        self.diffs    = []         # clear old data 
                    
        self.datadict['trigger_time']        = time.time()
        self.pi.write(self.DATA, pigpio.LOW)
        
        time.sleep(0.017) # 17 ms
        
        self.pi.set_mode(self.DATA, pigpio.INPUT)
        
        self.pi.set_watchdog(self.DATA, 200)

        time.sleep(0.2) 

        self.datadict['read_time']           = time.time()

        diffs_length = len(self.diffs)

        self.datadict['diffs']               = self.diffs
        self.datadict['diffs_length']        = diffs_length

        if diffs_length == 43:
            
            five   = [self.diffs[3+8*i : 3+8*(i+1)] for i in range(5)]

            values = []
            for thing in five:

                value = 0

                for diff in thing:
                    value = (value<<1) + int(diff>self.tick_threshold)

                values.append(value)

            HH, HL, TH, TL, check_sum = values

            four_sum = sum(values[:4])

            okay = four_sum == check_sum

            self.datadict['values']           = values
            self.datadict['checksum_okay']    = okay

            if okay:

                humidity = HH + 0.1*HL

                if TH & 128:   # temperature is negative
                    sign = -1.
                    TH = TH & 127
                else:
                    sign = +1.

                temperature = sign * (TH + 0.1*TL)

                self.datadict['humidity']    = humidity
                self.datadict['temperature'] = temperature
                self.last_read_is_good            = True        

        else:
            # print "diffs_length is not 43, it's ", diffs_length
            pass

        if self.last_read_is_good:
            self.statistics['ngoodreads']        += 1 
        else:
            self.statistics['nbadreads']         += 1 

        self._last_twenty_increment()

    # CANCEL THE WATCHDOG ON EXIT!
    def cancel(self):
        """Cancel the DHT22 sensor."""

        self.pi.set_watchdog(self.DATA, 0)

        if self.cb != None:
            self.cb.cancel()
            self.cb = None


class OLEDi2c(GPIO_DEVICE):
    
    devkind = "OLED"
    
    def __init__(self, box, name=None):

        self.instance_things = locals()

        GPIO_DEVICE.__init__(self, box, name)

        self.box.logger.info("OLEDi2c '{}' __init__".format(self.name))  

        self.screens        = []
        self.screendict     = dict()

        self.cmdmode        = 0x00
        self.datamode       = 0x40

        # for generating bytes to transfer to display
        self.npages         = 8
        self.nsegs          = 128

        # for generating images using PIL
        self.nx             = self.nsegs
        self.ny             = 8 * self.npages
        self.nxy            = (self.nx, self.ny)

        self.array = (np.zeros(self.nx*self.ny,
                               dtype=int).reshape(self.ny, self.nx))

        # Constants
        self.SSD1306_I2C_ADDRESS = 0x3C    # 011110+SA0+RW - 0x3C or 0x3D
        self.SSD1306_SETCONTRAST = 0x81
        self.SSD1306_DISPLAYALLON_RESUME = 0xA4
        self.SSD1306_DISPLAYALLON = 0xA5
        self.SSD1306_NORMALDISPLAY = 0xA6
        self.SSD1306_INVERTDISPLAY = 0xA7
        self.SSD1306_DISPLAYOFF = 0xAE
        self.SSD1306_DISPLAYON = 0xAF
        self.SSD1306_SETDISPLAYOFFSET = 0xD3
        self.SSD1306_SETCOMPINS = 0xDA
        self.SSD1306_SETVCOMDETECT = 0xDB
        self.SSD1306_SETDISPLAYCLOCKDIV = 0xD5
        self.SSD1306_SETPRECHARGE = 0xD9
        self.SSD1306_SETMULTIPLEX = 0xA8
        self.SSD1306_SETLOWCOLUMN = 0x00
        self.SSD1306_SETHIGHCOLUMN = 0x10
        self.SSD1306_SETSTARTLINE = 0x40
        self.SSD1306_MEMORYMODE = 0x20
        self.SSD1306_COLUMNADDR = 0x21
        self.SSD1306_PAGEADDR = 0x22
        self.SSD1306_COMSCANINC = 0xC0
        self.SSD1306_COMSCANDEC = 0xC8
        self.SSD1306_SEGREMAP = 0xA0
        self.SSD1306_CHARGEPUMP = 0x8D
        self.SSD1306_EXTERNALVCC = 0x1
        self.SSD1306_SWITCHCAPVCC = 0x2

        # Scrolling constants
        self.SSD1306_ACTIVATE_SCROLL = 0x2F
        self.SSD1306_DEACTIVATE_SCROLL = 0x2E
        self.SSD1306_SET_VERTICAL_SCROLL_AREA = 0xA3
        self.SSD1306_RIGHT_HORIZONTAL_SCROLL = 0x26
        self.SSD1306_LEFT_HORIZONTAL_SCROLL = 0x27
        self.SSD1306_VERTICAL_AND_RIGHT_HORIZONTAL_SCROLL = 0x29
        self.SSD1306_VERTICAL_AND_LEFT_HORIZONTAL_SCROLL = 0x2A

        # and also
        self.ADDR = self.SSD1306_I2C_ADDRESS #  = 0x3C    # 011110+SA0+RW - 0x3C or 0x3D
        
    def YAMLsetup(self, fname):

        try:
            with open(fname, 'r') as infile:
                self.yamldict = yaml.load(infile)
        except:
            print "yaml read failed for some reason"

        try:
            for sname, sdef in self.yamldict.items():
                screen = self.new_screen(sname)
                if 'fields' in sdef:
                    for fname, fdef in sdef['fields'].items():
                        xy0  = fdef['xy0']
                        args = fdef['args']
                        infopairs = args['info']
                        newpairs  = []
                        for devname, key in infopairs:
                            devicx = self.box.get_device(devname)
                            newpairs.append([devicx, key])
                        args['info'] = newpairs
                            
                        screen.new_field(fname, xy0, **args)

            print "successfull oled yaml setup!"

            for s in self.screens:
                print s
                for f in s.fields:
                    print '  ', f

            return self.yamldict
        
        except:
            print "yaml setup could not be implemented successfully for some reason"
            pass                        

    def new_screen(self, name):
        s = SCREEN(self.nxy, name)
        self.add_screen(s)
        return s

    def add_screen(self, s):
        self.screens.append(s)
        self.screendict[s.name] = s
        return s

    def initiate(self):
        
        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_DISPLAYOFF)            # 0xAE

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_SETDISPLAYCLOCKDIV)    # 0xD5
        self.bus.write_byte_data(self.ADDR, self.cmdmode, 0x80)                          # the suggested ratio 0x80

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_SETMULTIPLEX)           # 0xA8
        self.bus.write_byte_data(self.ADDR, self.cmdmode, 0x3F)

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_SETDISPLAYOFFSET)      # 0xD3
        self.bus.write_byte_data(self.ADDR, self.cmdmode, 0x0)                           # no offset

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_SETSTARTLINE | 0x0)    # line #0

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_CHARGEPUMP)            # 0x8D
        self.bus.write_byte_data(self.ADDR, self.cmdmode, 0x14)  # not external Vcc

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_MEMORYMODE)            # 0x20
        self.bus.write_byte_data(self.ADDR, self.cmdmode, 0x00)                          # 0x00 acts like ks0108

            # HEY I AM NOT SURE ABOUT THIS ONE!
            # We'd like VERTICAL addressing mode
            # which should be 0x01??

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_SEGREMAP | 0x1)

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_COMSCANDEC)

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_SETCOMPINS)            # 0xDA
        self.bus.write_byte_data(self.ADDR, self.cmdmode, 0x12)

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_SETCONTRAST)           # 0x81
        self.bus.write_byte_data(self.ADDR, self.cmdmode, 0xCF)  # not external Vcc

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_SETPRECHARGE)          # 0xd9
        self.bus.write_byte_data(self.ADDR, self.cmdmode, 0xF1)  # not external Vcc
            
        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_SETVCOMDETECT)         # 0xDB
        self.bus.write_byte_data(self.ADDR, self.cmdmode, 0x40)

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_DISPLAYALLON_RESUME)   # 0xA4

        self.bus.write_byte_data(self.ADDR, self.cmdmode, self.SSD1306_NORMALDISPLAY)         # 0xA6

        print "OLED inited!"

    def display_off(self):

        self.initiate()

        time.sleep(0.2)

        for thing in (self.SSD1306_DISPLAYOFF, ):

            self.bus.write_byte_data(self.ADDR, self.cmdmode, thing)

            time.sleep(0.2)

    def display_on(self):

        self.initiate()

        time.sleep(0.2)

        for thing in (self.SSD1306_DISPLAYON, self.SSD1306_DISPLAYALLON,
                      self.SSD1306_DISPLAYALLON_RESUME):

            self.bus.write_byte_data(self.ADDR, self.cmdmode, thing)

            time.sleep(0.2)

    def set_contrast(self, contrast):

        # contrast = 128    # would be 50% for example
        self.bus.write_byte_data(self.ADDR, 0x00, self.SSD1306_SETCONTRAST)
        self.bus.write_byte_data(self.ADDR, 0x00, contrast)

    def show_black(self):
        self.array[:] = 0
        self.show_array()

    def show_white(self):
        self.array[:] = 1
        self.show_array()
        
    def show_gray(self):
        self.array[:] = 0
        self.array[0::2, 0::2] = 1
        self.array[1::2, 1::2] = 1
        self.show_array()
        
    def show_array(self):
            self.pages = self.array.reshape(self.npages, 8, -1) # [::-1]  # invert it bitwise or this way
            self.bytelist = self._pages_to_bytes(self.pages)


            if 1 == 1:    #  Hey!  #  Hey!  double-check other works also!
                # Write buffer data.
                for byte in self.bytelist:
                    self.bus.write_byte_data(self.ADDR, self.datamode, byte)

            else:
                # Write buffer data.
                for i in range(0, len(self.bytelist), 31):
                    bus.write_i2c_block_data(self.ADDR, self.datamode, self.bytelist[i:i+31])

    def _pages_to_bytes(self, Zpages):
        twos = 2**np.arange(8)[:, None]
        Zbinpages = []
        for page in Zpages:
            bytez = (page.astype(bool)*twos).sum(axis=0)
            Zbinpages.append(bytez.tolist())

        allbytez = sum(Zbinpages, [])
        return allbytez

    def get_screen(self, scrn): # heytoday this is updated!

        if scrn in self.screens:
            sc = scrn
        else:
            try:
                sc = [s for s in self.screens if
                       s.name == scrn][0]
            except:
                print " oh, I couldn't find s.name = ", scrn
                print " all of the names are: ", [s.name for s in self.screens]
                sc = None
            
        return sc
        
    def show_screen(self, showscreen): # heytoday this is updated!

        if showscreen not in self.screens:    # screen object
            showscreen = self.get_screen(showscreen)   # screen name search

        if showscreen:
            self.array = showscreen.array.copy()
            self.show_array()
        else:
            print "screen not found"
        return showscreen

    def preview_screen(self, previewscreen):  # heytoday this is updated!

        if previewscreen not in self.screens:    # screen object
            previewscreen = self.get_screen(previewscreen)   # screen name search

        if previewscreen:
            screen.preview_me()
        
    def preview_me(self):

        plt.figure()
        plt.imshow(self.array, cmap='gray', interpolation='nearest')
        plt.show()
        
    def update_and_show_screen(self, showscreen):  # heytoday this is updated!

        showscreen = self.get_screen(showscreen)

        if showscreen:
            showscreen.update()
            self.show_screen(showscreen)

    def array_stats(self):

        print "self.array.min(), self.array.max(): ", self.array.min(), self.array.max()
        print "self.array.shape, self.array.dtype: ", self.array.shape, self.array.dtype

    def _embed(self, small_array, big_array, big_index):
        """Overwrites values in big_array starting at big_index with those in small_array"""
        slices = [np.s_[i:i+j] for i,j in zip(big_index, small_array.shape)]
        big_array[slices] = small_array
        try:
            big_array[slices] = small_array
        except:
            print "field embed failed"

    def show_image(self, filename, resize_method, conversion_method, threshold=None):

        self.img0   = Image.open(filename)
        w0, h0 = self.img0.size

        self.box.logger.info("showimage opened size w0, h0 {}".format((w0, h0)))  
        print "showimage opened size w0, h0 {}".format((w0, h0))

        if resize_method == 'stretch':

            new_size = (self.nx, self.ny)

            self.imgr = self.img0.resize(new_size)

            self.box.logger.info("showimage new_size stretch {}".format(new_size))  
            print "showimage new_size stretch {}".format(new_size)

        elif resize_method == 'fit':

            wscale = float(self.nx)/float(w0)
            hscale = float(self.ny)/float(h0)

            if hscale <= wscale:
                print "hscale <= wscale"
                new_size = (int(w0*hscale), self.ny)
            else:
                print "hscale > wscale"
                new_size = (self.nx, int(h0*hscale))

            self.imgr = self.img0.resize(new_size)

            self.box.logger.info("showimage new_size fit {}".format(new_size))
            print "showimage new_size fit {}".format(new_size)

        else:

            self.imgr = None

            self.box.logger.error("showimage new_size failed")  
            print "showimage new_size failed"

        if self.imgr:

            if conversion_method in ('default', 'dither'):

                self.imgc  = self.imgr.convert("1")

                self.box.logger.info("showimage convert default".format(new_size))
                print "showimage convert default".format(new_size)

            elif conversion_method in ('threshold', ):

                self.imgr8 = self.imgr.convert("L")
                self.imgc  = self.imgr8.point(lambda x: 0 if x < threshold else 1, mode='1')

                self.box.logger.info("showimage convert threshold".format(new_size))
                print "showimage convert threshold".format(new_size)

        else:

            imgc = None

            self.box.logger.error("showimage conversion failed")
            print "showimage conversion failed"

        if self.imgc:
            
            wni, hni = self.imgc.size
            array    = np.array(list(self.imgc.getdata())).reshape(hni, wni)

            bigarray = np.zeros(self.ny*self.nx, dtype=int).reshape(self.ny, self.nx)

            sa0, sa1 = array.shape
            sb0, sb1 = bigarray.shape

            hoff = max(0, (sb0-sa0)/2-1)
            woff = max(0, (sb1-sa1)/2-1)
            print "hoff = ", hoff
            print "woff = ", woff
            
            self._embed(array, bigarray, (hoff, woff))

            print "bigarray.shape: ", bigarray.shape
            arrayf = bigarray.astype(float)
            arrayf = arrayf / arrayf.max()

            self.array = bigarray.copy()

            self.show_array()
            # plt.figure()
            # plt.imshow(arrayf)
            # plt.show()

    

class MCP3008bb(GPIO_DEVICE):
    
    devkind="MCP3008"
    
    def __init__(self, box, name=None, CSbar=None, MISO=None,
                 MOSI=None, SCLK=None, SPI_baud=None, Vref=None):
        
        self.instance_things = locals()

        GPIO_DEVICE.__init__(self, box, name)

        self.box.logger.info("MCP3008bb '{}' __init__".format(self.name))  

        self.CSbar         = CSbar
        self.MISO          = MISO
        self.MOSI          = MOSI
        self.SCLK          = SCLK
        if SPI_baud == None:
            SPI_baud = 10000
        self.SPI_baud      = SPI_baud
        self.SPI_MODE      = 1      # this is important!
        self.Vref          = Vref

        self.nbits         = 10   # MCP3008 is always 10 bits?? this may change

        try:
            self.pi.bb_spi_close(self.CSbar)
        except:
            pass

        print "    #### Okay, here we go! "
        print "self.CSbar:    ", self.CSbar
        print "self.MISO:     ", self.MISO
        print "self.MOSI:     ", self.MOSI
        print "self.SCLK:     ", self.SCLK
        print "self.SPI_baud: ", self.SPI_baud
        print "self.SPI_MODE: ", self.SPI_MODE

        self.pi.bb_spi_open(self.CSbar, self.MISO, self.MOSI, 
                       self.SCLK, self.SPI_baud, self.SPI_MODE)

    def _digitize_one_channel(self, n_channel, clear_datadict=False):

        if clear_datadict:
            self.datadict = dict()

        # NOTE check if iterable, or an integer

        three_bytes      = [1, (8+n_channel)<<4, 0]

        ct, data         = self.pi.bb_spi_xfer(self.CSbar, three_bytes)

        adc_convert_time = time.time()

        counts        = ((data[1]<<8) | data[2]) & 0x3FF

        self.datadict['adc_convert_time'] = adc_convert_time
        self.datadict['channel ' + str(n_channel) + ' counts'] = counts

        return counts, adc_convert_time

    def measure_one_voltage(self, channel, clear_datadict=False):

        self.last_read_is_good            = False
        self.statistics['nreads']        += 1 

        adc_value, adc_convert_time = self._digitize_one_channel(channel, clear_datadict)

        voltage = self.Vref * float(adc_value) / (2**self.nbits - 1.)

        self.datadict['channel ' + str(channel) + ' voltage'] = voltage

        self.last_read_is_good                = True       

        if self.last_read_is_good:
            self.statistics['ngoodreads']    += 1
        else: 
            self.statistics['nbadreads']     += 1 

        self._last_twenty_increment()

        return voltage, adc_value, adc_convert_time


class MOS_gas_sensor(GPIO_DEVICE):
    
    devkind="MOS_gas_sensor"
    
    def __init__(self, box, name, ADC, channel, Rseries, 
                 Calibrationdata, 
                 use_loglog = False, gasname=None,
                 atlimitsisokay = False):

        self.instance_things = locals()

        GPIO_DEVICE.__init__(self, box, name)

        self.box.logger.info("MOS_gas_sensor '{}' __init__".format(self.name))

        if ADC not in self.box.devices:
            ADC            = self.box.get_device(ADC)
        
        self.ADC                = ADC
        self.Vref               = 3.3
        self.channel            = channel
        self.Rseries            = Rseries
        self.Calibrationdata    = Calibrationdata
        self.use_loglog         = use_loglog
        self.gasname            = gasname
        self.atlimitsisokay     = atlimitsisokay

        Resistdata,    ppmdata    = zip(*self.Calibrationdata)

        self.ppmdata              = ppmdata
        self.Resistdata           = Resistdata

        self.use_loglog           = use_loglog

        self.ppmdata              = ppmdata
        self.Resistdata           = Resistdata

    def read(self):

        self.last_read_is_good            = False
        self.statistics['nreads']        += 1 

        self.datadict = dict()    # clear old data

        # get data
        v, adc_val, adc_time = self.ADC.measure_one_voltage(self.channel,
                                                            clear_datadict=False)  # make ADC measurement
        if v < 0.1 or v > self.Vref - 0.1:
            v = None   # don't continue with pathaological voltage

        try:
            R_sensor = self.Rseries*(self.Vref/v - 1.)
        except:
            R_sensor = None  # don't continue with pathaological resistance

        try:
            ppm = np.interp(R_sensor, self.Resistdata, self.ppmdata)
        except:
            ppm = None  # don't continue with pathaological interpolation
        
        if self.atlimitsisokay:
            if ppm <= 0 or ppm < min(self.ppmdata) or ppm > max(self.ppmdata):
                ppm = None
        else:
            if ppm <= 0 or ppm <= min(self.ppmdata) or ppm >= max(self.ppmdata):
                ppm = None

        if ppm != None:
            ppm = int(ppm)

        self.datadict['read_time']        = time.time()
        self.datadict['ppm']              = ppm
        self.datadict['R_sensor']         = R_sensor
        self.datadict['voltage']          = v
        self.datadict['adc_value']        = adc_val
        self.datadict['adc_convert_time'] = adc_time

        if ppm != None:
            self.last_read_is_good            = True       

        if self.last_read_is_good:
            self.statistics['ngoodreads']    += 1 
        else: 
            self.statistics['nbadreads']     += 1 

        self._last_twenty_increment()


class SCREEN(object):
    
    devkind = "SCREEN"
    
    def __init__(self, nxy, name=None):
        
        self.name        = name
        self.fields      = dict()
        self.nxy         = nxy
        self.nx, self.ny = self.nxy
        
    def __repr__(self):
        return ('{self.__class__.__name__}({self.name})'
                .format(self=self))

    def new_field(self, name, xy0, wh=None,
                  fmt=None, fontdef=None, fontsize=None,
                  threshold=None, info=None):
        
        f = FIELD(name, wh, fmt, fontdef, fontsize, threshold, info)
        self.add_field(f, xy0)
        return f
    
    def add_field(self, f, xy0): 
        self.fields[f] = xy0
        f.screens.append(self)
        return f
            
    def get_field(self, fieldname): 

        try:
            field = [f for f in self.fields if f.name == fieldname][0]
        except:
            print " oh, I couldn't find f.name = ", fieldname
            print " all of the names are: ", [f.name for f in self.fields]
            field = None
            
        return field

    def _embed(self, small_array, big_array, big_index):
        """Overwrites values in big_array starting at big_index with those in small_array"""
        slices = [np.s_[i:i+j] for i,j in zip(big_index, small_array.shape)]
        big_array[slices] = small_array
        try:
            big_array[slices] = small_array
        except:
            print "field embed failed"

    def _update_array(self):

        self.array = np.zeros(self.nx * self.ny, dtype=int).reshape(self.ny, self.nx)

        for field, xy0 in self.fields.items():

            self._embed(field.array, self.array, xy0[::-1])

    def update(self):   # heytoday this is updated!

        for field in self.fields:

            field.update()

        self._update_array()
        
    def preview_me(self):

        plt.figure()
        plt.imshow(self.array, cmap='gray', interpolation='nearest')
        plt.show()

    def update_and_preview_me(self):  # heytoday this is updated!

        self.update()
        self.preview_me()


    def show_image(self, filename, resize_method, conversion_method, threshold=None):

        img0   = Image.open(filename)
        w0, h0 = img0.width, img0.height

        self.box.logger.info("showimage opened size w0, h0 {}".format((w0, h0)))  
        print "showimage opened size w0, h0 {}".format((w0, h0))

        if resize_method == 'stretch':

            new_size = (self.w, self.h)

            imgr = img0.resize(new_size)

            self.box.logger.info("showimage new_size stretch {}".format(new_size))  
            print "showimage new_size stretch {}".format(new_size)

        elif resize_method == 'fit':

            wscale = float(self.nx)/float(w0)
            hscale = float(self.ny)/float(h0)

            if hscale <= wscale:
                print "hscale <= wscale"
                new_size = (int(w0*hscale), self.ny)
            else:
                print "hscale > wscale"
                new_size = (self.nx, int(h0*hscale))

            imgr = img0.resize(new_size)

            self.box.logger.info("showimage new_size fit {}".format(new_size))
            print "showimage new_size fit {}".format(new_size)

        else:

            imgr = None

            self.box.logger.error("showimage new_size failed")  
            print "showimage new_size failed"

        if imgr:

            if conversion_method in ('default', 'dither'):

                imgc  = imgr.convert("1")

                self.box.logger.info("showimage convert default".format(new_size))
                print "showimage convert default".format(new_size)

            elif conversion_method in ('threshold', ):

                imgr8 = imgr.convert("L")
                imgc  = imgr8.point(lambda x: 0 if x < threshold else 1, mode='1')

                self.box.logger.info("showimage convert threshold".format(new_size))
                print "showimage convert threshold".format(new_size)

        else:

            imgc = None

            self.box.logger.error("showimage conversion failed")
            print "showimage conversion failed"

        if imgc:
            
            wni, hni = imgc.width, imgc.height
            array    = np.array(list(imgc.getdata())).reshape(hni, wni)

            bigarray = np.zeros(self.h*self.w, dtype=int).reshape(self.h, self.w)

            sa0, sa1 = array.shape
            sb0, sb1 = bigarray.shape

            hoff = max(0, (sb0-sa0)/2-1)
            woff = max(0, (sb1-sa1)/2-1)
            print "hoff = ", hoff
            print "woff = ", woff
            
            _embed(array, bigarray, (hoff, woff))

            print "bigarray.shape: ", bigarray.shape
            arrayf = bigarray.astype(float)
            arrayf = arrayf / arrayf.max()
            plt.figure()
            plt.imshow(arrayf)
            plt.show()

    

class FIELD(object):
    
    devkind = "FIELD"
    
    def __init__(self, name, wh=None,
                 fmt=None, fontdef=None, fontsize=None,
                 threshold=None, info=None):

        self.name            = name
        self.wh              = wh

        self.screens         = []

        try:
            self.w, self.h   = self.wh[:2]
        except:
            pass

        self.fmt             = fmt

        self.fontdef         = fontdef

        if type(fontsize) is int:
            self.fontsize    = fontsize
        else:
            self.fontsize    = 14

        if self.fontdef == 'default':
            self.font  = ImageFont.load_default()
        elif type(self.fontdef) is str:
            if self.fontdef[-4:].lower() == '.ttf':
                self.font = ImageFont.truetype(self.fontdef,
                                               self.fontsize)
            else:
                print "fontdef problem!"
            
        self.threshold       = threshold
        self.info            = info

    def __repr__(self):
        return ('{self.__class__.__name__}({self.name})'
                .format(self=self))

    def update(self):

        self._update_string()
        self._generate_array()

    def _get_pairs(self, fmt):
        pairs =[(m.start(), m.end()) for m in re.finditer('{([^{)]*)}', fmt)]
        return pairs

    def _stringit(self, fmt, data):
        xchar = '##'
        xchar_alt = u'\u25A1\u25A0'
        pairs = self._get_pairs(fmt)
        if len(pairs) == 0:
            s = fmt.format()
        else:
            keepers = [fmt[:pairs[0][0]]]
            for i in range(len(pairs)-1):
                keepers.append(fmt[pairs[i][1]:pairs[i+1][0]])
            keepers.append(fmt[pairs[-1][1]:])
            zingers = [fmt[p[0]:p[1]] for p in pairs]
            newdata = []
            newfmt  = keepers[0]
            for d, z, k in zip(data, zingers, keepers[1:]):
                if d == None:
                    newfmt += xchar + k
                else:
                    newdata.append(d)
                    newfmt += z + k
            s = newfmt.format(*newdata)
        return s

    def _update_string(self):
        self.string = ''
        self.values = []
        for device, key in self.info:
            try:
                dev = device # self.box.get_device(device)
                value = dev.datadict[key]
                self.values.append(value)
            except:
                self.values.append(None)

        self.string = self._stringit(self.fmt, self.values)

        # self.string = self.fmt.format(*self.values)

    def _generate_array(self):
        # print " trying to generate my array! ", self.name
        if type(self.threshold) in (int, float):
            self.imageRGB = Image.new('RGB', (self.w, self.h))
            self.draw  = ImageDraw.Draw(self.imageRGB)
        
            self.draw.text((0,0), self.string, font=self.font,
                           fill=(255, 255, 255, 255))  # R, G, B alpha
        
            self.image8bit = self.imageRGB.convert("L")
            self.image1bit = self.image8bit.point(lambda x: 0 if x < self.threshold else 1, mode='1')
            self.image     = self.image1bit
            self.arrayRGB  = np.array(list(self.imageRGB.getdata())).reshape(self.h, self.w, 3)
            self.array8bit  = np.array(list(self.image8bit.getdata())).reshape(self.h, self.w)
            self.array1bit  = np.array(list(self.image1bit.getdata())).reshape(self.h, self.w)
        else:
            self.image = Image.new('1', (self.w, self.h)) 
            self.draw  = ImageDraw.Draw(self.image)
       
            self.draw.text((0,0), self.string, font=self.font, fill=255)

        self.ww, self.hh = self.image.size

        self.array = np.array(list(self.image.getdata())).reshape(self.hh, -1)

    def preview_me(self):

        plt.figure()
        plt.imshow(self.array, cmap='gray', interpolation='nearest')
        plt.show()

    def update_and_preview_me(self):

        self.update()
        self.preview_me()


def PiM25YAMLreader(fname):

    with open(fname, 'r') as infile:
        d = yaml.load(infile)

    nboxes = len(d)

    boxes = []

    for i, (boxname, boxdef) in enumerate(d.items()):

        boxargs = boxdef['args']

        print '  BOXARGS: ', boxargs

        box = BOX(boxname, **boxargs)
        
        box.logger.info("BOX '{}' instantiated from YAML file '{}'".format(box.name, fname))

        boxes.append(box)

        GPIO_devices = boxdef['GPIO devices']
        print "Box GPIO devices: ", GPIO_devices.keys()

        for j, (devname, devdef) in enumerate(GPIO_devices.items()):
            use_method = devdef['method']
            method  = getattr(box, use_method)
            if 'args' in devdef:
                devargs = devdef['args']
                device = method(devname, **devargs)
            else:
                device = method(devname)
            if 'oled' in device.devkind.lower() and 'screens' in devdef:
                for sname, sdef in devdef['screens'].items():
                    screen = device.new_screen(sname)
                    if 'fields' in sdef:
                        for fname, fdef in sdef['fields'].items():
                            xy0  = fdef['xy0']
                            args = fdef['args']
                            infopairs = args['info']
                            newpairs  = []
                            for devname, key in infopairs:
                                devicx = box.get_device(devname)
                                newpairs.append([devicx, key])
                            args['info'] = newpairs
                                
                            screen.new_field(fname, xy0, **args)
        LASS_devices = boxdef['LASS devices']
        print "Box LASS devices: ", LASS_devices.keys()
        for LASSname, LASSdevice in LASS_devices.items():
            newLASS = box.new_LASS(LASSname)
            newLASS.set_static_location(**LASSdevice['static location'])
            sourcedict = LASSdevice['sources']
            newsourcedict = dict()
            for key, src in sourcedict.items():
                if key == 'gassensors':
                    print 'gassensors = ', src
                    for gs in src:
                        source = box.get_device(gs)
                        print '   zzzzzz: ', source.name
                else:
                    if src not in ('static', 'system'):
                        source = box.get_device(src)
                    else:
                        source = src
                    newsourcedict[key] = source
            newLASS.set_sources(**newsourcedict)
            
    return boxes


