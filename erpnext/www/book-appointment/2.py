import frappe
import datetime


def get_context(context):
    context.date = frappe.form_dict['date']
    settings = frappe.get_doc('Appointment Booking Settings')
    holiday_list = frappe.get_doc('Holiday List', settings.holiday_list)
    if(is_holiday(context.date,holiday_list)):
        context.is_holiday = True
        return context
    get_time_slots(context.date,settings)
    # time_slots = get_time_slots(date)
    return context

def is_holiday(date,holiday_list):
    for holiday in holiday_list.holidays:
        if holiday.holiday_date.isoformat() == date:
            print('matched')
            return True
    return False



def _deltatime_to_time(deltatime):
    return (datetime.datetime.min + deltatime).time()

weekdays = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]