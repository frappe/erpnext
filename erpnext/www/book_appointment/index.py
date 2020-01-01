import frappe
import datetime
import json
import pytz


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

no_cache = 1


def get_context(context):
	is_enabled = frappe.db.get_single_value('Appointment Booking Settings', 'enable_scheduling')
	if is_enabled:
		return context
	else:
		frappe.local.flags.redirect_location = '/404'
		raise frappe.Redirect

@frappe.whitelist(allow_guest=True)
def get_appointment_settings():
	settings = frappe.get_doc('Appointment Booking Settings')
	settings.holiday_list = frappe.get_doc('Holiday List', settings.holiday_list)
	return settings

@frappe.whitelist(allow_guest=True)
def get_timezones():
	import pytz
	return pytz.all_timezones

@frappe.whitelist(allow_guest=True)
def get_appointment_slots(date, timezone):
	# Convert query to local timezones
	format_string = '%Y-%m-%d %H:%M:%S'
	query_start_time = datetime.datetime.strptime(date + ' 00:00:00', format_string)
	query_end_time = datetime.datetime.strptime(date + ' 23:59:59', format_string)
	query_start_time = convert_to_system_timezone(timezone, query_start_time)
	query_end_time = convert_to_system_timezone(timezone, query_end_time)
	now = convert_to_guest_timezone(timezone, datetime.datetime.now())

	# Database queries
	settings = frappe.get_doc('Appointment Booking Settings')
	holiday_list = frappe.get_doc('Holiday List', settings.holiday_list)
	timeslots = get_available_slots_between(query_start_time, query_end_time, settings)

	# Filter and convert timeslots
	converted_timeslots = []
	for timeslot in timeslots:
		converted_timeslot = convert_to_guest_timezone(timezone, timeslot)
		# Check if holiday
		if _is_holiday(converted_timeslot.date(), holiday_list):
			converted_timeslots.append(dict(time=converted_timeslot, availability=False))
			continue
		# Check availability
		if check_availabilty(timeslot, settings) and converted_timeslot >= now:
			converted_timeslots.append(dict(time=converted_timeslot, availability=True))
		else:
			converted_timeslots.append(dict(time=converted_timeslot, availability=False))
	date_required = datetime.datetime.strptime(date + ' 00:00:00', format_string).date()
	converted_timeslots = filter_timeslots(date_required, converted_timeslots)
	return converted_timeslots

def get_available_slots_between(query_start_time, query_end_time, settings):
	records = _get_records(query_start_time, query_end_time, settings)
	timeslots = []
	appointment_duration = datetime.timedelta(
		minutes=settings.appointment_duration)
	for record in records:
		if record.day_of_week == WEEKDAYS[query_start_time.weekday()]:
			current_time = _deltatime_to_datetime(query_start_time, record.from_time)
			end_time = _deltatime_to_datetime(query_start_time, record.to_time)
		else:
			current_time = _deltatime_to_datetime(query_end_time, record.from_time)
			end_time = _deltatime_to_datetime(query_end_time, record.to_time)
		while current_time + appointment_duration <= end_time:
			timeslots.append(current_time)
			current_time += appointment_duration
	return timeslots


@frappe.whitelist(allow_guest=True)
def create_appointment(date, time, tz, contact):
	format_string = '%Y-%m-%d %H:%M:%S'
	scheduled_time = datetime.datetime.strptime(date + " " + time, format_string)
	# Strip tzinfo from datetime objects since it's handled by the doctype
	scheduled_time = scheduled_time.replace(tzinfo = None)
	scheduled_time = convert_to_system_timezone(tz, scheduled_time)
	scheduled_time = scheduled_time.replace(tzinfo = None)
	# Create a appointment document from form
	appointment = frappe.new_doc('Appointment')
	appointment.scheduled_time = scheduled_time
	contact = json.loads(contact)
	appointment.customer_name = contact.get('name', None)
	appointment.customer_phone_number = contact.get('number', None)
	appointment.customer_skype = contact.get('skype', None)
	appointment.customer_details = contact.get('notes', None)
	appointment.customer_email = contact.get('email', None)
	appointment.status = 'Open'
	appointment.insert()
	return appointment

# Helper Functions
def filter_timeslots(date, timeslots):
	filtered_timeslots = []
	for timeslot in timeslots:
		if(timeslot['time'].date() == date):
			filtered_timeslots.append(timeslot)
	return filtered_timeslots

def convert_to_guest_timezone(guest_tz, datetimeobject):
	guest_tz = pytz.timezone(guest_tz)
	local_timezone = pytz.timezone(frappe.utils.get_time_zone())
	datetimeobject = local_timezone.localize(datetimeobject)
	datetimeobject = datetimeobject.astimezone(guest_tz)
	return datetimeobject

def convert_to_system_timezone(guest_tz,datetimeobject):
	guest_tz = pytz.timezone(guest_tz)
	datetimeobject = guest_tz.localize(datetimeobject)
	system_tz = pytz.timezone(frappe.utils.get_time_zone())
	datetimeobject = datetimeobject.astimezone(system_tz)
	return datetimeobject

def check_availabilty(timeslot, settings):
	return frappe.db.count('Appointment', {'scheduled_time': timeslot}) < settings.number_of_agents

def _is_holiday(date, holiday_list):
	for holiday in holiday_list.holidays:
		if holiday.holiday_date == date:
			return True
	return False


def _get_records(start_time, end_time, settings):
	records = []
	for record in settings.availability_of_slots:
		if record.day_of_week == WEEKDAYS[start_time.weekday()] or record.day_of_week == WEEKDAYS[end_time.weekday()]:
			records.append(record)
	return records


def _deltatime_to_datetime(date, deltatime):
	time = (datetime.datetime.min + deltatime).time()
	return datetime.datetime.combine(date.date(), time)


def _datetime_to_deltatime(date_time):
	midnight = datetime.datetime.combine(date_time.date(), datetime.time.min)
	return (date_time-midnight)