import frappe
import datetime


def get_context(context):
    # Get query parameters
    date = frappe.form_dict['date']
    tz = frappe.form_dict['tz']
    tz = int(tz)
    # Database queries
    settings = frappe.get_doc('Appointment Booking Settings')
    holiday_list = frappe.get_doc('Holiday List', settings.holiday_list)
    # Format datetimes
    format_string = '%Y-%m-%d %H:%M:%S'
    start_time = datetime.datetime.strptime(date+' 00:00:00', format_string)
    end_time = datetime.datetime.strptime(date+' 23:59:59', format_string)
    # Convert to ist
    start_time = _convert_to_ist(start_time, tz)
    end_time = _convert_to_ist(end_time, tz)
    timeslots = get_available_slots_between(start_time, end_time, settings)
    converted_timeslots = []
    print('Appointments')
    print(frappe.get_list('Appointment',fields=['from_time']))
    for timeslot in timeslots:
        if timeslot > end_time or timeslot < start_time:
            pass
        else:
            if frappe.db.count('Appointment',{'from_time':start_time.time()}) < settings.number_of_agents:
                converted_timeslots.append(dict(time=_convert_to_tz(timeslot, tz), unavailable=False))
            else:
                converted_timeslots.append(dict(time=_convert_to_tz(timeslot, tz),unavailable=True))

    context.timeslots = converted_timeslots
    context.date = date
    return context

def _is_holiday(date, holiday_list):
    for holiday in holiday_list.holidays:
        if holiday.holiday_date.isoformat() == date:
            return True
    return False

def _convert_to_ist(datetime_object, timezone):
    offset = datetime.timedelta(minutes=timezone)
    datetime_object = datetime_object + offset
    offset = datetime.timedelta(minutes=-330)
    datetime_object = datetime_object - offset
    return datetime_object

def _convert_to_tz(datetime_object, timezone):
    offset = datetime.timedelta(minutes=timezone)
    datetime_object = datetime_object - offset
    offset = datetime.timedelta(minutes=-330)
    datetime_object = datetime_object + offset
    return datetime_object

def get_available_slots_between(start_time_parameter, end_time_parameter, settings):
    records = get_records(start_time_parameter, end_time_parameter, settings)
    timeslots = []
    appointment_duration = datetime.timedelta(
        minutes=settings.appointment_duration)
    for record in records:
        if record.day_of_week == weekdays[start_time_parameter.weekday()]:
            current_time = _deltatime_to_datetime(
                start_time_parameter, record.from_time)
            end_time = _deltatime_to_datetime(
                start_time_parameter, record.to_time)
        elif record.day_of_week == weekdays[end_time_parameter.weekday()]:
            current_time = _deltatime_to_datetime(
                end_time_parameter, record.from_time)
            end_time = _deltatime_to_datetime(
                end_time_parameter, record.to_time)
        while current_time + appointment_duration <= end_time:
            timeslots.append(current_time)
            current_time += appointment_duration
    return timeslots


def get_records(start_time, end_time, settings):
    records = []
    for record in settings.availability_of_slots:
        if record.day_of_week == weekdays[start_time.weekday()] or record.day_of_week == weekdays[end_time.weekday()]:
            records.append(record)
    return records


def _deltatime_to_datetime(date, deltatime):
    time = (datetime.datetime.min + deltatime).time()
    return datetime.datetime.combine(date.date(), time)


weekdays = ["Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday", "Sunday"]
