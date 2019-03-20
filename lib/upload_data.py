import PiM25_config as Conf
import os

def organize(msg, pm_s, loc_s):
    if pm_s == 1:
        msg += '|app=%s' % (Conf.APP_ID)
        msg += '|device=%s' % (Conf.DEVICE)
        msg += '|device_id=%s' % (Conf.DEVICE_ID)
        msg += '|tick=%f' % (Conf.tick)
        msg += '|fmt_opt=%d' % (Conf.fmt_opt)
        msg += '|ver_format=%d' % (Conf.ver_format)
        msg += '|gps_fix=%d' % (Conf.gps_fix)
        msg += '|ver_app=%s' % (Conf.ver_app)
        msg += '|FAKE_GPS=%d' % (Conf.FAKE_GPS)
    
        Restful_URL = Conf.Restful_URL
        # print(msg)
        ## ready to upload data ##
        restful_str = "wget -O /tmp/last_upload.log \"" + Restful_URL + "device_id=" + Conf.DEVICE_ID + "&msg=" + msg + "\""
        
        # print(restful_str)

        try:
            os.system(restful_str)
        except Exception as e:
            ## upload failed ##
            print(e)

    else:
        ## PM2.5 data missing ##
        print("Error: Won't upload data")
