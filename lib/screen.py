import time
import datetime
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
import Image
import ImageDraw
import ImageFont

def display(data):
    print(data)
    ## Raspberry Pi pin configuration ##
    RST = 24

    ## 128x32 display with hardware I2C ##
    disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST)

    ## Initialize library ##
    disp.begin()

    ## Clear display ##
    disp.clear()
    disp.display()

    PiM25_logo = Image.open("/home/pi/PiM25/PLOT/logo.png").resize((128, 32)).convert("1")

    ## Create blank image for drawing ##
    width = disp.width
    height = disp.height

    ## Display Sensor Information ##
    # sensor_image = Image.new('1',(width,height))
    # draw = ImageDraw.Draw(sensor_image)
    # draw.text((0,0),'PM2.5: ', fill = 1)
    # draw.text((0,8),'Temperature: ', fill = 1)
    # draw.text((0,16),'Humidity: ', fill = 1)

    now = datetime.datetime.now()
    today_date = now.strftime("%d %b %y")
    today_time = now.strftime("%H:%M:%S")

    ## Display Time ##
    Time_image = Image.new('1',(width,height))
    draw = ImageDraw.Draw(Time_image)
    draw.text((0,0),'Date: ' + today_date, fill = 1)
    draw.text((0,8),'Time: ' + today_time, fill = 1)
   
    try:
        disp.image(PiM25_logo)
        disp.display()
        time.sleep(3)
        disp.image(Time_image)
        disp.display()
        time.sleep(3)
        disp.image(PiM25_logo)
        disp.display()
        
    except Exception as e:
        print(e)
        disp.clear()
        disp.display()
