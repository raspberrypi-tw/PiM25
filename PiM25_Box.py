#!/usr/bin/env python
# -*- coding: utf-8 -*-

# SUGGESTED CONNECTIONS, but you can of course do it differenlty!
# SUGGESTED CONNECTIONS, but you can of course do it differenlty!
################################################################             
#            Raspberry Pi 3 GPIO Pinout;           Corner -->  #
#                     (pin 1)  | (pin 2)                       #                  
#br   OLED/GPS Vcc     +3.3V   |  +5.0V    PM25 G3 pin 1 Vcc br#
#y    OLED SDA        GPIO  2  |  +5.0V    MOS Gas Sensor +5V p#     
#o    OLED SCL        GPIO  3  |  GND      MCP3008 GND/GND   br#
#                     GPIO  4  | UART TX                       #
#r    OLED GND         GND     | UART RX                       #
#o    MCP3008 CSbar   GPIO 17  | GPIO 18                       #
#y    MCP3008 MOSI    GPIO 27  |  GND                          #
#g    MCP3008 MISO    GPIO 22  | GPIO 23                       #
#r    MCP3008 Vcc/Vref +3.3V   | GPIO 24   PM25 G3 pin 5 TX   g#
#bl   MCP3008 CLK     GPIO 10  |  GND      PM25 G3 pin 2 GND  o#
#                     GPIO  9  | GPIO 25                       #                      #
#                     GPIO 11  | GPIO  8                       #
#                      GND     | GPIO  7                       #
#                     Reserved | Reserved                      #
#                     GPIO  5  |  GND                          #
#                     GPIO  6  | GPIO 12   GPS TX              #
#                     GPIO 13  |  GND      GPS GND             #
#b   DHT22 POWER      GPIO 19  | GPIO 16                       #
#w   DHT22 DATA       GPIO 26  | GPIO 20                       #
#gy  DHT22 GND         GND     | GPIO 21                       #
#                    (pin 39)  |(pin 40)                       #                  
################################################################

from PiM25updated42 import BOX
import time

# make a box
box = BOX('my box', use_WiFi=False,
          use_SMBus=True, use_pigpio=True)

dht   = box.new_DHT22bb('my dht', DATA=26, POWER=19)
g3    = box.new_G3bb('my g3', DATA=24, collect_time = 3.0)
# gps   = box.new_GPSbb('my gps', DATA=12, collect_time = 3.0) for now use static dummy
oled  = box.new_OLEDi2c('my oled', rotate180=True)
adc   = box.new_MCP3008bb('my adc', MISO=22, MOSI=27,
                          CSbar=17, SCLK=10, Vref=3.3)

# if you don't have MOS gas sensors, just use a resistor divider to make a voltage for the ADC
CO2   = box.new_MOS_gas_sensor('my CO2', ADC=adc, channel=5,
                               Rseries=1000,
                               Calibrationdata=[[100, 10000], [1000, 1000], [10000, 100]],
                               use_loglog=False, gasname='CO2',
                               atlimitsisokay=True)
CO    = box.new_MOS_gas_sensor('my CO', ADC=adc, channel=6,
                               Rseries=2000,
                               Calibrationdata=[[100, 10000], [1000, 1000], [10000, 100]],
                               use_loglog=False, gasname='CO',
                               atlimitsisokay=True)

mylogconfig = {dht:['temperature', 'humidity'], 
               g3:['PM25', 'PM1', 'PM10'],
               CO2:['ppm'], CO:['ppm']}

mylog = box.new_LOG('mylog.txt', 'mylog')
mylog.configure(mylogconfig)

lass = box.new_LASS('mylass')
lass.set_static_location(latlon=(25.033661, 121.564841), alt=550.)  # TPE101

lass.set_sources(humsrc=dht, tempsrc=dht,
                 pm25src=g3, pm1src=g3, pm10src=g3, 
                 timedatesrc='system', GPSsrc=gps)
gpsstatic = {'latitude': lass.static_lat,
             'longitude':lass.static_lon,
             'altitude': lass.static_alt }
gps     = box.new_Dummy('my gps', gpsstatic)
timedate = box.new_Dummy('sys timedate')

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
    oled.show_image('TPE101small.png', resize_method='fit',
                    conversion_method='threshold', threshold=60)
    for d in readables:
        d.read()
    systimedic = box.get_system_timedate_dict()
    timedate.datadict.update(systimedic)

        
    mylog.build_and_save_entry(sysinfo_interval=10)

    lass.build_entry()

    for cycle in range(2):
        for s in oled.screens:
            s.update()
            oled.show_screen(s)
            time.sleep(1)
