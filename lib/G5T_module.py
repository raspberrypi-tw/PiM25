def bytes2hex(s):
    return "".join("{:02x}".format(c) for c in s)

def data_read(dstr, temp_info):
    ## standard data style ##
    standard_head = "424d001c"
    data_len = 64

    index = dstr.find(standard_head)

    if(index == -1 or len(dstr) < 64):
        ## sense failed ##
        return temp_info, -1 

    else:
        ## pm2.5 data that we need ##
        data_slice = dstr[index : index + data_len]
            
        ## cf_pm1 ##
        temp_info["CFPM1.0"] = (int(data_slice[8] + data_slice[9] + data_slice[10] + data_slice[11], 16))

        ## cf_pm2.5 ##
        temp_info["CFPM2.5"] = (int(data_slice[12] + data_slice[13] + data_slice[14] + data_slice[15], 16))

        ## cf_pm10 ##
        temp_info["CFPM10"] = (int(data_slice[16] + data_slice[17] + data_slice[18] + data_slice[19], 16))

        ## pm1 ##
        temp_info["s_d2"] = (int(data_slice[20] + data_slice[21] + data_slice[22] + data_slice[23], 16))

        ## pm2.5 ##
        temp_info["s_d0"] = (int(data_slice[24] + data_slice[25] + data_slice[26] + data_slice[27], 16))

        ## pm10 ##
        temp_info["s_d1"] = (int(data_slice[28] + data_slice[29] + data_slice[30] + data_slice[31], 16))

        ## temperature ##
        temp_info["s_t0"] = (int(data_slice[48] + data_slice[49] + data_slice[50] + data_slice[51], 16) / 10)

        ## humidity ##
        temp_info["s_h0"] = (int(data_slice[52] + data_slice[53] + data_slice[54] + data_slice[55], 16) / 10)

    return temp_info, 1

