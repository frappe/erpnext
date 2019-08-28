import frappe

def get_context(context):
    settings = frappe.get_doc('Appointment Booking Settings')
    holiday_list = frappe.get_doc('Holiday List',settings.holiday_list)
    holidays = []
    for holiday in holiday_list.holidays:
        print(str(holiday.holiday_date))
        holidays.append(str(holiday.holiday_date))
    context.holidays = holidays
    context.from_date = holiday_list.from_date
    context.to_date = holiday_list.to_date
    timezones = frappe.get_all('Timezone',fields=["timezone_name","offset"])
    context.timezones = timezones
    
    return context

