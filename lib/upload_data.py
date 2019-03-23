import PiM25_config as Conf
import os

def organize(temp_info, pm_s, loc_s):
    if pm_s == 1:
        temp_info["device_id"] = Conf.DEVICE_ID
        temp_info["tick"] = Conf.tick
    
        Restful_URL = Conf.Restful_URL

        msg = ""
        for label, value in temp_info.items():
            msg += "|" + label + "=" + str(value)

        ## ready to upload data ##
        restful_str = "wget -O /tmp/last_upload.log \"" + Restful_URL + "device_id=" + Conf.DEVICE_ID + "&msg=" + msg + "\""
        

        try:
            os.system(restful_str)
        except Exception as e:
            ## upload failed ##
            print(e)

    else:
        ## PM2.5 data missing ##
        print("Error: Won't upload data")

    return temp_info
