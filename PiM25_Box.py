#!/usr/bin/env python
# -*- coding: utf-8 -*-

# SUGGESTED CONNECTIONS, but you can of course do it differenlty!
##############################################################             
#           Raspberry Pi 3 GPIO Pinout;           Corner --> #
#                    (pin 1)  | (pin 2)                      #                  
#  OLED/GPS Vcc       +3.3V   |  +5.0V    GPS NEO6 Vcc       #
#  OLED SDA          GPIO  2  |  +5.0V    PM25 G5 pin 1 Vcc b#     
#  OLED SCL          GPIO  3  |  GND      PM25 G5 pin 2 GND o#
#                    GPIO  4  | UART TX                      #
#  OLED/Gas GND       GND     | UART RX                      #
#                    GPIO 17  | GPIO 18   GPS NEO6 pin 5 TX  #
#                    GPIO 27  |  GND      GPS NEO6 GND       #
#                    GPIO 22  | GPIO 23                      #
#r MCP3008 Vcc/Vref   +3.3V   | GPIO 24   PM25 G5 pin 5 TX  g#
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

from PiM25 import BOX
import time

# make a box
box = BOX('my box', use_WiFi=False,
          use_SMBus=True, use_pigpio=True)

dht   = box.new_DHT22bb('my dht', DATA=26, POWER=19)
g5    = box.new_G5bb('my g5', DATA=24, collect_time = 3.0)
#oled  = box.new_OLEDi2c('my oled')
#adc   = box.new_MCP3008bb('my adc', MISO=22, MOSI=27,
#                          CSbar=17, SCLK=10, Vref=3.3)

# if you don't have MOS gas sensors, just use a resistor divider to make a voltage for the ADC
#CO2   = box.new_MOS_gas_sensor('my CO2', ADC=adc, channel=5,
#                               Rseries=1000,
#                               Calibrationdata=[[100, 10000], [1000, 1000], [10000, 100]],
#                               use_loglog=False, gasname='CO2',
#                               atlimitsisokay=True)
#CO    = box.new_MOS_gas_sensor('my CO', ADC=adc, channel=6,
#                               Rseries=2000,
#                               Calibrationdata=[[100, 10000], [1000, 1000], [10000, 100]],
#                               use_loglog=False, gasname='CO',
#                               atlimitsisokay=True)

mylogconfig = {dht:['temperature', 'humidity'], 
               g5:['PM25', 'PM1', 'PM10'], }

mylog = box.new_LOG('mylog.txt', 'mylog')
mylog.configure(mylogconfig)

lass = box.new_LASS('mylass')
timedate = box.new_Dummy('sys timedate')
gps     = box.new_GPSbb('my gps', DATA=18)
lass.set_sources(humsrc=g5, tempsrc=g5,
                 pm25src=g5, pm1src=g5, pm10src=g5, 
                 GPSsrc=gps,
                 timedatesrc='system')
timedate = box.new_Dummy('sys timedate')

readables = [d for d in box.devices if hasattr(d, 'read')]

for d in readables:
    d.read()
    print d, 'read is good: ', d.last_read_is_good


#oled.YAMLsetup('oledyaml.yaml')
#oled.initiate()
#oled.display_on()
#for thing in ('show_white', 'show_black', 'show_gray'):
#    getattr(oled, thing)()

while True:
    print "loop!"
    #oled.show_image('pim25b.bmp', resize_method='fit',
    #                conversion_method='threshold', threshold=60)
    for d in readables:
        d.read()
    systimedic = box.get_system_timedate_dict()
    timedate.datadict.update(systimedic)
        
    mylog.build_and_save_entry(sysinfo_interval=10)

    lass.build_entry()

    for cycle in range(2):
    #    for s in oled.screens:
    #        s.update()
    #        oled.show_screen(s)
            time.sleep(1)
