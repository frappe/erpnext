import frappe
import datetime
import nepali_datetime
from datetime import timedelta
import nepali_datetime

@frappe.whitelist()
def get_converted_date(date):
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
        date = date[0:10]
        date_to_convert = datetime.date(int(date[0]), int(date[1]),int(date[2]))
        return nepali_datetime.date.from_datetime_date(date_to_convert).strftime("%D-%n-%K")+ " "+ str(nepali_time)