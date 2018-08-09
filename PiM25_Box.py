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
#  OLED/Gas GND       GND     | UART RX                      #                    GPIO 17  | GPIO 18   PM25 G3 pin 5 TX  g#
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

from PiM25 import BOX
import time

# make a box
box = BOX('my box', use_WiFi=True,
              use_SMBus=True, use_pigpio=True)

dht   = box.new_DHT22bb('my dht', DATA=25, POWER=8)
g3    = box.new_G3bb('my g3', DATA=18, collect_time = 3.0)
oled  = box.new_OLEDi2c('my oled')
adc   = box.new_MCP3008bb('my adc', MISO=13, MOSI=19,
                          CSbar=26, SCLK=6, Vref=3.3)
CO2   = box.new_MOS_gas_sensor('my CO2', ADC=adc, channel=1,
                               Rseries=1000,
                               Calibrationdata=[[100, 10000], [1000, 1000], [10000, 100]],
                               use_loglog=False, gasname='CO2',
                               atlimitsisokay=True)
dummy = box.new_Dummy('my dummy', dummydatadict={'x':42})

mylogconfig = {dht:['temperature', 'humidity'], 
               g3:['PM25', 'PM1', 'PM10'],
               CO2:['ppm'], dummy:['x']}

mylog = box.new_LOG('mylog.txt', 'mylog')
mylog.configure(mylogconfig)

lass = box.new_LASS('mylass')
lass.set_static_location(latlon=(25.033661, 121.564841), alt=550.)  # TPE101
lass.set_sources(humsrc=dht, tempsrc=dht,
                 pm25src=g3, pm1src=g3, pm10src=g3, 
                 timedatesrc='system', GPSsrc='static')

readables = [d for d in box.devices if hasattr(d, 'read')]

for d in readables:
    d.read()
    print d, 'read is good: ', d.last_read_is_good

if True:
    oled.YAMLsetup('oledyaml.yaml')

oled.initiate()
oled.display_on()
for thing in ('show_white', 'show_black', 'show_gray'):
    getattr(oled, thing)()

while True:
    print "loop!" 
    for d in readables:
        d.read()
        
    mylog.build_and_save_entry(sysinfo_interval=10)

    lass.build_entry()

    print lass.LASS_string

    for s in oled.screens:
        s.update()
        oled.show_screen(s)
        time.sleep(1)
