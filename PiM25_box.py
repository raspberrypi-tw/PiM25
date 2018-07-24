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

s3.new_field('COa', [2, 10], wh=[120, 24],
             fmt='CO (ppm) {0:.1f}', fontdef='Arial Unicode.ttf',
             fontsize=18, threshold=30, info=((CO, 'ppm'),))

s3.new_field('COb', [2, 40], wh=[120, 24],
             fmt='CO (ppm) {0:.1f}', fontdef='Arial Unicode.ttf',
             fontsize=18, threshold=225, info=((CO, 'ppm'),))



oled.initiate()
oled.display_on()
for thing in ('show_white', 'show_black', 'show_gray'):
    getattr(oled, thing)()

# Define your loop for operation 

wait = 10.  # seconds

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
