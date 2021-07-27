import frappe
import datetime
import nepali_datetime
from datetime import timedelta

@frappe.whitelist()
def get_converted_date(date):
    country = frappe.db.get_single_value("System Settings",'country')
    date = date.split("-")
    date_to_convert = datetime.date(int(date[0]), int(date[1]),int(date[2]))
    if country == 'Nepal':
        return nepali_datetime.date.from_datetime_date(date_to_convert).strftime("%D-%n-%K")