import datetime
import json
import zoneinfo

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint
from frappe.utils.data import get_system_timezone

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

no_cache = 1


def get_context(context):
	handle_appointment_booking_disabled()

	return context


def handle_appointment_booking_disabled():
	if not frappe.get_single_value("Appointment Booking Settings", "enable_appointment_portal"):
		frappe.redirect_to_message(
			_("Appointment Scheduling Disabled"),
			_("Appointment Scheduling has been disabled for this site"),
			http_status_code=302,
			indicator_color="red",
		)
		raise frappe.Redirect


@frappe.whitelist(allow_guest=True)
def get_appointment_settings():
	handle_appointment_booking_disabled()
	settings = frappe.get_single_value(
		"Appointment Booking Settings",
		["advance_booking_days", "appointment_duration", "success_redirect_url"],
		as_dict=True,
	)
	return settings


@frappe.whitelist(allow_guest=True)
def get_timezones():
	handle_appointment_booking_disabled()
	return zoneinfo.available_timezones()


# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method -- reviewed: public booking page; returns free slots only, booking must be enabled
@frappe.whitelist(allow_guest=True)
def get_appointment_slots(date: str, timezone: str):
	# Convert query to local timezones
	handle_appointment_booking_disabled()
	validate_timezone(timezone)
	query_start_time = parse_datetime(date, "00:00:00")
	query_end_time = parse_datetime(date, "23:59:59")
	query_start_time = convert_to_system_timezone(timezone, query_start_time)
	query_end_time = convert_to_system_timezone(timezone, query_end_time)
	now = convert_to_guest_timezone(timezone, frappe.utils.now_datetime())

	# Database queries
	settings = frappe.get_single_value(
		"Appointment Booking Settings",
		["holiday_list", "appointment_duration", "number_of_agents", "availability_of_slots"],
		as_dict=True,
	)
	holiday_list = frappe.get_doc("Holiday List", settings.holiday_list)
	timeslots = get_available_slots_between(query_start_time, query_end_time, settings)
	# fetch the day's booked slots once instead of querying per timeslot
	booked_times = get_booked_slot_times_for(timeslots, settings.appointment_duration)

	# Filter and convert timeslots
	converted_timeslots = []
	for timeslot in timeslots:
		converted_timeslot = convert_to_guest_timezone(timezone, timeslot)
		# Check if holiday
		# holidays are business dates: check the slot's system-time date
		if _is_holiday(timeslot.date(), holiday_list):
			converted_timeslots.append(dict(time=converted_timeslot, availability=False))
			continue
		# Check availability
		if is_slot_available(timeslot, booked_times, settings) and converted_timeslot >= now:
			converted_timeslots.append(dict(time=converted_timeslot, availability=True))
		else:
			converted_timeslots.append(dict(time=converted_timeslot, availability=False))
	date_required = parse_datetime(date, "00:00:00").date()
	converted_timeslots = filter_timeslots(date_required, converted_timeslots)
	return converted_timeslots


def get_available_slots_between(query_start_time, query_end_time, settings):
	records = _get_records(query_start_time, query_end_time, settings)
	timeslots = []
	appointment_duration = datetime.timedelta(minutes=settings.appointment_duration)
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


# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method -- reviewed: public booking page; rate limited, slot and capacity validated, unverified until confirmed by email
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=300)
def create_appointment(date: str, time: str, tz: str, contact: str | dict):
	handle_appointment_booking_disabled()
	validate_timezone(tz)
	scheduled_time = parse_datetime(date, time)
	# Strip tzinfo from datetime objects since it's handled by the doctype
	scheduled_time = scheduled_time.replace(tzinfo=None)
	scheduled_time = convert_to_system_timezone(tz, scheduled_time)
	scheduled_time = scheduled_time.replace(tzinfo=None)
	# Create a appointment document from form
	appointment = frappe.new_doc("Appointment")
	appointment.scheduled_time = scheduled_time
	contact = frappe.parse_json(contact)
	appointment.customer_name = contact.get("name", None)
	appointment.customer_phone_number = contact.get("number", None)
	appointment.customer_skype = contact.get("skype", None)
	appointment.customer_details = contact.get("notes", None)
	appointment.customer_email = contact.get("email", None)
	appointment.created_through_portal = 1
	appointment.insert(ignore_permissions=True)
	return appointment


# Helper Functions
def validate_timezone(timezone: str):
	try:
		zoneinfo.ZoneInfo(timezone)
	except (zoneinfo.ZoneInfoNotFoundError, ValueError):
		frappe.throw(_("{0} is not a valid time zone").format(timezone))


def parse_datetime(date: str, time: str) -> datetime.datetime:
	try:
		return datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
	except ValueError:
		frappe.throw(_("{0} {1} is not a valid date and time").format(date, time))


def filter_timeslots(date, timeslots):
	filtered_timeslots = []
	for timeslot in timeslots:
		if timeslot["time"].date() == date:
			filtered_timeslots.append(timeslot)
	return filtered_timeslots


def convert_to_guest_timezone(guest_tz, datetimeobject):
	guest_tz = zoneinfo.ZoneInfo(guest_tz)
	local_timezone = zoneinfo.ZoneInfo(get_system_timezone())
	datetimeobject = datetimeobject.replace(tzinfo=local_timezone)
	datetimeobject = datetimeobject.astimezone(guest_tz)
	return datetimeobject


def convert_to_system_timezone(guest_tz, datetimeobject):
	guest_tz = zoneinfo.ZoneInfo(guest_tz)
	datetimeobject = datetimeobject.replace(tzinfo=guest_tz)
	system_tz = zoneinfo.ZoneInfo(get_system_timezone())
	datetimeobject = datetimeobject.astimezone(system_tz)
	return datetimeobject


def get_booked_slot_times_for(timeslots, appointment_duration):
	if not timeslots:
		return []

	from erpnext.crm.doctype.appointment.appointment import get_booked_slot_times

	duration = datetime.timedelta(minutes=appointment_duration)
	return get_booked_slot_times(min(timeslots) - duration, max(timeslots) + duration)


def is_slot_available(timeslot, booked_times, settings):
	# no agents means unlimited capacity, as in Appointment.validate_available_time_slot
	if not cint(settings.number_of_agents):
		return True

	# mirror the server capacity check: count non-Closed appointments whose
	# duration window overlaps this slot, without a per-slot query
	duration = datetime.timedelta(minutes=settings.appointment_duration)
	lower, upper = timeslot - duration, timeslot + duration
	overlapping = sum(1 for booked in booked_times if lower < booked < upper)
	return overlapping < settings.number_of_agents


def _is_holiday(date, holiday_list):
	# half-day holidays still take appointments, as the server allows them
	return any(h.holiday_date == date and not h.is_half_day for h in holiday_list.holidays)


def _get_records(start_time, end_time, settings):
	records = []
	for record in settings.availability_of_slots:
		if (
			record.day_of_week == WEEKDAYS[start_time.weekday()]
			or record.day_of_week == WEEKDAYS[end_time.weekday()]
		):
			records.append(record)
	return records


def _deltatime_to_datetime(date, deltatime):
	time = (datetime.datetime.min + deltatime).time()
	return datetime.datetime.combine(date.date(), time)


def _datetime_to_deltatime(date_time):
	midnight = datetime.datetime.combine(date_time.date(), datetime.time.min)
	return date_time - midnight
