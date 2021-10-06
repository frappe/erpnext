import frappe
import datetime
import nepali_datetime
from datetime import timedelta
import nepali_datetime
import pyconvertdigits
@frappe.whitelist()
def get_converted_date(date):
    convertDigits = pyconvertdigits.conDigits()
    if len(date) <= 10:
        date = date[0:10]
        date = date.split("-")
        date_to_convert = datetime.date(int(date[0]), int(date[1]),int(date[2]))
        return nepali_datetime.date.from_datetime_date(date_to_convert).strftime("%D-%n-%K")
    else: 
        seperated_time_date = date.split(" ")
        date = seperated_time_date[0].split("-")
        time = seperated_time_date[1].split(":")
        gorgian_time = datetime.datetime(int(date[0]), int(date[1]), int(date[2]),int(time[0]),int(time[1]))
        nepali_time = gorgian_time+timedelta(hours=.25)
        split_t_n_d = str(nepali_time).split(' ')
        nepali_time = split_t_n_d[1].split(':')
        date = date[0:10]
        date_to_convert = datetime.datetime(int(date[0]), int(date[1]),int(date[2]))
        h = convertDigits.to_hindi(int(nepali_time[0]))
        m = convertDigits.to_hindi(int(nepali_time[1]))
        s = convertDigits.to_hindi(int(nepali_time[2]))
        if len(s) == 1:
            s = '०'+s
        converted_time = "{0}:{1}:{2}".format(h,m,s)
        return nepali_datetime.datetime.from_datetime_datetime(date_to_convert).strftime("%D-%n-%K")+" "+converted_time
        
