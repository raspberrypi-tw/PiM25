import time
import pigpio
import commands

def data_read(all_lines):
    gprmc = [s for s in all_lines if "$GPRMC" in s]
    if gprmc is not None:
        gdata = gprmc[0].split(",")
        status    = gdata[1]
        latitude  = gdata[3]      #latitude
        dir_lat   = gdata[4]      #latitude direction N/S
        longitute = gdata[5]      #longitute
        dir_lon   = gdata[6]      #longitude direction E/W
        speed     = gdata[7]      #Speed in knots
        trCourse  = gdata[8]      #True course
        try:
            receive_t = gdata[1][0:2] + ":" + gdata[1][2:4] + ":" + gdata[1][4:6]
        except ValueError:
            pass
 
        try:
            receive_d = gdata[9][0:2] + "/" + gdata[9][2:4] + "/" + gdata[9][4:6] 
        except ValueError:
            pass
        
        print "time : %s, latitude : %s(%s), longitude : %s(%s), speed : %s, True Course : %s, Date : %s" %  (receive_t, latitude , dir_lat, longitute, dir_lon, speed, trCourse, receive_d)
        return latitude, dir_lat, longitute, dir_lon, speed

RX = 24
GPS_LAT = 25.1933
GPS_LON = 121.7870
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

pi.set_mode(RX, pigpio.INPUT)
try:
    pi.bb_serial_read_close(RX)
except Exception as e:
    pass

while True:
    try:
        pi.bb_serial_read_open(RX, 9600)
        time.sleep(0.9)
        (status, data) = pi.bb_serial_read(RX)
        if status:
            print("read_something")
            lines = ''.join(chr(x) for x in data).splitlines()
            print(data)
            data_read(lines)
        else:
            print("read nothing")
 
    except Exception as e:
        print(e)
        pi.bb_serial_read_close(RX)
        print("close success")
    try:
        pi.bb_serial_read_close(RX)
    except:
        pass
    time.sleep(5)

pi.stop()
print("End")

