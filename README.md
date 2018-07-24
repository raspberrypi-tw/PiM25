# PiM25
An easy-to-use Python script for connecting a Raspberry Pi-based PM2.5 monitor to the LASS system.

While a stand-alone AirBox is cool, using a Raspberry Pi to power it is a bit of overkill for something that you put and forget. A simple, reliable, industrial micro-controller (Arduino or other) is more desirable for a put-and-forget airbox that you install and leave somewhere.

The goal here is to find a way to take full advantage of the Raspberry Pi’s capability in order to do something better.

Raspberry pi has several important advantages, and PiM25 software’s goal is to make all of these advantages available

You can:
* Have multiple, virtual boxes
* Compare different sensors head-to-head in real time.
* Do local logging, or electronic reporting of sensors beyond those needed for a standard AirBox report. They allow for many, and for mobile and battery operated support (battery level, battery charge/discharge, motion speed, CPU usage percent) as well as additional sensors beyond (PM1, 2.5, 10, temp, humid) like 
  * add toxic and irritating gasses
  * light levels
  * radiation
  * rain and precipitation
  * barometric pressure
  * loud noises
  * wind speed and direction

Multiple, virtual LASS boxes to support multiple sensor sets in the same location

How to “build a box”.

There are a few ways. 

* You can write a standard, simple python script. Make a box instance, then make sensor instances from it.

* You can do it interactively from a Python prompt. Similarly to the script, make a box instance, then make sensor instances from it.

* Generate the whole thing predefined in a .yaml dictionary. Use PiM25.PiM25YAMLreader(‘filename.yaml’) 

You can also combine any or all of the above!

Once you are done, you can SAVE your configuration as a .yaml file using PiM25.PiM25YAMLwriter(‘filename.yaml’) That way you can “rebuild” your box the next time you start your project, exactly as it existed when you were last developing it.

METHOD 1: Python script.

from PiM25_UPDATED import BOX
import time
from itertools import cycle
import matplotlib.pyplot as plt

# make a box
box = BOX('my box', use_WiFi=True,
              use_SMBus=True, use_pigpio=True)

# add your sensors
dht  = box.new_DHT22bb('my dht', DATA=17, POWER=27)

g3   = box.new_G3bb('my dht', DATA=24, collect_time=3.0)

adc  = box.new_MCP3008bbspi('my adc',CSbar=26, MISO=13,
                            MOSI=19, SCLK=6, Vref=3.3 )

CO   = box.new_MOS_gas_sensor('my CO sensor', ADC='my adc', channel=1,
                              Rseries=1000,
                              Calibrationdata=[[10,5000],[100,2200],[1000,777]],
                              logCalibrationdata=[[10,5000],[100,2200],[1000,777]],
                              use_loglog=False, gasname='CO')


# add your oled screen setup

oled = box.new_OLEDi2c('my oled')

s1 = oled.new_screen('T and H')

s1.new_field('temp', [2, 5], wh=[120, 24],
             fmt='T(C) {0:.1f}', fontdef='Arial Unicode.ttf',
             fontsize=20, info=[[dht, 'temperature']])
s1.new_field('humid', [2, 35], wh=[120, 24],
             fmt='H(%) {0:.1f}', fontdef='Arial Unicode.ttf',
             fontsize=20, info=[[dht, 'humidity']])

s2 = oled.new_screen('particles')

s2.new_field('PMbig', [2, 5], wh=[120, 24],
             fmt='PM25 {0:.0f}', fontdef='Arial Unicode.ttf',
             fontsize=20, info=((g3, 'PM25'),))
s2.new_field('PMsmall', [2, 35], wh=[120, 24],
             fmt='PM1 {0:.0f}, PM10 {0:.0f}', fontdef='default',
             fontsize=20, info=((g3, 'PM1'), (g3, 'PM10')))


s3 = oled.new_screen('gasses')

s3.new_field('COa', [2, 30], wh=[120, 24],
             fmt='CO (ppm) {0:.1f}', fontdef='Arial Unicode.ttf',
             fontsize=18, info=((CO, 'ppm'),))



oled.initiate()
oled.display_on()
for thing in ('show_white', 'show_black', 'show_gray'):
    getattr(oled, thing)()

# Define your loop for operation 

wait = 7.  # seconds

# Go!
while True:

    oled.show_gray()

    dht.read()
    g3.read()
    adc.digitize_one_channel(1)
    CO.read()

    # or just use box.read_all()
    # lass.build_and_send_to_LASS()
    # print lass.LASS_string

    for s in oled.screens:
        s.update_all()

    tnext   = time.time() + wait

    screenz = cycle(oled.screens)
            
    while time.time() < tnext:
        s = screenz.next()
        oled.show_screen(s)
        time.sleep(1.5)



METHOD 2: Python interactive.
     should be similar or identical, just typed line-by-line


METHOD 3: .yaml definition.

    my box:
      args: {'use_WiFi': True, 'use_pigpio': True, 'use_SMBus': True}
      LASS devices:
        my LASS:
          static location: {'latlon':[25.03366, 121.564841], 'alt':550.0}
          sources: {'humsrc':'my dht', 'tempsrc':'my dht', 'pm1src':'my gthree', 'pm25src':'my gthree', 'pm10src':'my gthree', 
                    'timedatesrc':'system', 'GPSsrc':'static', 'gassensors':[]}
      GPIO devices:
        my dht:
          method: new_DHT22bb
          args: {'DATA':17, 'POWER':27}
        my gthree:
          method: new_G3bb
          args: {'DATA':24, 'collect_time':3.0}
        my oled: 
          method: new_OLEDi2c
          screens:
            T and H:
              fields:
                temp:
                  args: {'wh':[120, 24],
                         'fmt':'T(C) {0:.1f}', 'fontdef':'Arial Unicode.ttf',
                         'fontsize':20, 'info':[['my dht', 'temperature']]}
                  xy0: [2, 5]
                humid:
                  args: {'wh':[120, 24],
                         'fmt':'H(%) {0:.1f}', 'fontdef':'Arial Unicode.ttf',
                         'fontsize':20, 'info':[['my dht', 'humidity']]}
                  xy0: [2, 35]
            particles:
              fields:
                PMbig:
                  args: {'wh':[120, 24],
                         'fmt':'PM25 {0:.0f}', 'fontdef':'Arial Unicode.ttf',
                         'fontsize':20, 'info':[['my gthree', 'PM25']]}
                  xy0: [2, 5]
                PMsmall:
                  args: {'wh':[120, 24],
                         'fmt':'PM1 {0:.0f}, PM10 {0:.0f}', 'fontdef':'default',
                         'info':[['my gthree', 'PM1'], ['my gthree', 'PM10']]}
                  xy0: [2, 35]


And the python to run it is currently like this. In the next version, it will be completely automated

    boxes = reader('mybox_documentation.yaml')

    box   = boxes[0]
    lass  = box.LASS_devices[0]
    log   = box.LOG_devices[0]

    box.get_device('my oled').initiate()
    box.get_device('my oled').display_on()
    box.get_device('my oled').show_gray()

    # Define your loop for operation 

    wait = 10.  # seconds

    # Go!
    while True:

        box.read_all()
        lass.build_and_send_to_LASS()
        # print lass.LASS_string
        log.build_and_save_entry()

        for s in oled.screens():
            s.update_all()

        tnext   = time.time() + wait

        screenz = cycle(box.screens)
                
        while time.time() < tnext:
            s = next(screenz)
            oled.show_screen(s)
            time.sleep(1)

----

Here is a quick review of python methods:

    BOX
    .clear_all_device_datadicts()
    .read_all_devices()
    .get_system_timedate_dict()
    .make_a_pi()
    .WiFi_setstatus()
    .get_WiFi_is_on()
    .WiFi_on()
    .WiFi_off()
    .get_mac_address()
    .print_some_system_info()
    .get_system_datetime()
    .show_CPU_temp()
    .get_system_datetime()
    .add_device(dev)

    # some wrappers…..
    .new_Dummy()
    .new_DHT22bb()
    .new_G3bb()
    .new_GPSbb()
    .new_MCP3008bbspi()
    .new_MOS_gas_sensor()
    .new_OLEDi2c()
    .new_LASS()
    .new_LOG()
    .get_system_datetime()

    LASS
        .set_static_location(latlon, alt)
        .set_sources(self, humsrc=None, tempsrc=None, pm25src=None,
                        pm1src=None, pm10src=None, timedatesrc=None,
                    GPSsrc=None, gassensors=None)
        .build_entry()
        .send_to_LASS()
        .view_LASS_entry()

    LOG
        .configure()
        .build_entry()
        .save_entry()

    GPIO_DEVICE
    .get_my_current_instance_info() 
    .get_my_original_instance_info() 
        Dummy
            .read()
        DHT22bb
            .read()
            .cancel()
        MCP3008bbSPI
            .digitize_one_channel()
            .measure_one_voltage()
            MOS_gas_sensor_ppm()
                 .read()
        MOS_gas_sensor
            .read()
        RTCi2c
            .read()
            .set_time()
        G3bb
            .read()
        GPSbb
            .read()
        OLEDi2c
            .new_screen()
            .add_screen(screen object)
            .initiate()
            .display_on()
            .set_contrast()
            .show_black()
            .show_white()
            .show_gray()
            .show_screen(screen object)
            .update_all_and_show_screen(screen object) 
            .show_array()
            .preview_me()   
            SCREEN
                .__init__()
                .__repr__()    
                .new_field()
                .add_field()
                .update_all()
                .preview_me()
                .update_all_and_preview_me()  
                FIELD
                    .__init__()
                    .__repr__()    
                    .update()
                    .preview_me()