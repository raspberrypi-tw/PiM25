def read_last_gps(info):
    lastest_gps = open("/home/pi/Local/gps_info.txt","r")
    file_list = lastest_gps.readlines()[0].replace("\n", "").split(",")
    info["gps_num"] = int(file_list[0])
    info["gps_lat"] = float(file_list[1])
    info["gps_lon"] = float(file_list[3])
    lastest_gps.close()
    return info

def data_read(lines, temp_info):
    
    try:
        gprmc = [rmc for rmc in lines if "$GPRMC" in rmc]
        gpgga = [gga for gga in lines if "$GPGGA" in gga]

        if len(gprmc) and len(gpgga):
            ## sense success ##
            gga = gpgga[0].split(",")
            gdata = gprmc[0].split(",")
            valid = gdata[2]
            if valid is 'A':
                ## valid status ##
                ## print("GPS valid status") ##
                satellite = int(gga[7])
                status    = gdata[1]      ## status ##
                latitude  = gdata[3]      ## latitude ##
                dir_lat   = gdata[4]      ## latitude direction N/S ##
                longitude = gdata[5]      ## longitude ##
                dir_lon   = gdata[6]      ## longitude direction E/W ##
                speed     = gdata[7]      ## Speed in knots ##

                ## transform type ##
                speed = float(speed) * 1.825

                print "latitude : %s(%s), longitude : %s(%s), speed : %f" %  (latitude , dir_lat, longitude, dir_lon, speed)

                if speed <= 10:     
                    ## moving slow ##
                    ## collect gps location ##
                    temp_info["gps_num"] = satellite
                    temp_info["gps_lat"] = (latitude * 100)
                    temp_info["gps_lon"] = (longitude * 100)
                    
                    ## store GPS information ##
                    lastest_gps = open("/home/pi/Local/gps_info.txt","w") 
                    lastest_gps.write(str(satellite) + "," + str(latitude * 100) + "," + dir_lat + "," + str(longitude * 100) + "," + dir_lon)
                    lastest_gps.close() 
                else:
                    ## moving fast ##
                    print("out of speed")
            else:
                ## invalid status ##
                ## use last time gps location ##
                temp_info = read_last_gps(temp_info)
        else:
            ## sense failed,  GPS can't find GPRMC and GPGGA ##
            ## use last gps location ##
            temp_info = read_last_gps(temp_info)

    except Exception as e:
        print(e)
        ## use last gps location ##
        temp_info = read_last_gps(temp_info)

    return temp_info

