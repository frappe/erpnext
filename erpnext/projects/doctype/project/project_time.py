from __future__ import unicode_literals
import frappe
import datetime
import time
from time import gmtime, strftime
@frappe.whitelist()
def times_check(from1,to,first_email,second_email,daily_time_to_send,weekly_time_to_send):

    hoursF, min, sec = map(int,from1.split(':'))
    hoursT, min, sec = map(int, to.split(':'))
    hoursFE,min, sec = map(int, first_email.split(':'))
    hoursSE,min, sec = map(int, second_email.split(':'))
    hoursDE,min, sec = map(int, daily_time_to_send.split(':'))
    hoursWE,min, sec = map(int, weekly_time_to_send.split(':'))

    from_reminder = datetime.time(hoursF, 00, 00)
    to_reminder = datetime.time(hoursT, 00, 00)
    first_email_reminder = datetime.time(hoursFE, 00, 00)
    second_email_reminder = datetime.time(hoursSE, 00, 00)
    daily_time_to_send_reminder = datetime.time(hoursDE, 00, 00)
    weekly_time_to_send_reminder = datetime.time(hoursWE, 00, 00)

    return from_reminder.strftime('%H:%M:%S'),to_reminder.strftime('%H:%M:%S'),first_email_reminder.strftime('%H:%M:%S'),second_email_reminder.strftime('%H:%M:%S'),daily_time_to_send_reminder.strftime('%H:%M:%S'),weekly_time_to_send_reminder.strftime('%H:%M:%S')
