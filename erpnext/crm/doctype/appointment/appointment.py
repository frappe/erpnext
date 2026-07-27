# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from collections import Counter
from datetime import timedelta
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as add_assignment
from frappe.model.document import Document
from frappe.share import add_docshare
from frappe.utils import add_to_date, cint, date_diff, get_datetime, get_url, getdate, now, now_datetime
from frappe.utils.data import sha256_hash

from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class Appointment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		appointment_with: DF.Link | None
		calendar_event: DF.Link | None
		created_through_portal: DF.Check
		customer_details: DF.LongText | None
		customer_email: DF.Data
		customer_name: DF.Data
		customer_phone_number: DF.Data | None
		customer_skype: DF.Data | None
		email_verified: DF.Check
		party: DF.DynamicLink | None
		scheduled_time: DF.Datetime
		status: DF.Literal["Open", "Unverified", "Closed"]
		verification_token: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.validate_status_update()
		if not self.has_value_changed("scheduled_time"):
			return

		self.validate_backdated_booking()

		if is_appointment_scheduling_enabled():
			self.validate_advanced_booking()
			self.validate_holiday()
			self.validate_slot_timing()

		self.validate_available_time_slot()

	def validate_status_update(self):
		if not self.has_value_changed("status"):
			return

		if not self.created_through_portal:
			if self.status == "Unverified":
				frappe.throw(_("Appointments created manually cannot have 'Unverified' status."))
			return

		if self.status == "Unverified" and self.email_verified:
			frappe.throw(_("A verified appointment cannot be moved back to 'Unverified' status."))

		if self.status == "Open" and not self.email_verified:
			frappe.throw(
				_("An appointment booked through the portal can only be opened via email verification.")
			)

	def validate_backdated_booking(self):
		if get_datetime(self.scheduled_time) < now_datetime():
			frappe.throw(_("Appointment cannot be scheduled for a past time."))

	def validate_advanced_booking(self):
		advance_booking_days = cint(get_booking_settings().advance_booking_days)

		if advance_booking_days and date_diff(self.scheduled_time, now_datetime()) > advance_booking_days:
			frappe.throw(
				_("Appointment can only be scheduled up to {0} day(s) in advance.").format(
					advance_booking_days
				)
			)

	def validate_holiday(self):
		holiday_list = get_booking_settings().holiday_list

		if not holiday_list:
			frappe.throw(_("Please add a valid Holiday List on Appointment Booking Settings."))

		if is_holiday(holiday_list, getdate(self.scheduled_time)):
			frappe.throw(_("Appointment cannot be scheduled on a holiday."))

	def validate_slot_timing(self):
		settings = get_booking_settings()
		if not settings.availability_of_slots:
			frappe.throw(_("No availability of slots are found. Please add on Appointment Booking Settings."))

		scheduled_time = get_datetime(self.scheduled_time)
		day_of_week = WEEKDAYS[scheduled_time.weekday()]
		slot_start = timedelta(
			hours=scheduled_time.hour, minutes=scheduled_time.minute, seconds=scheduled_time.second
		)
		slot_end = slot_start + timedelta(minutes=cint(settings.appointment_duration))

		for slot in settings.availability_of_slots:
			if slot.day_of_week == day_of_week and slot.from_time <= slot_start and slot_end <= slot.to_time:
				return

		frappe.throw(_("Appointment must be scheduled within the available slot timings."))

	def validate_available_time_slot(self):
		settings = get_booking_settings()
		if not cint(settings.number_of_agents):
			return

		# the locking read serializes concurrent bookings for the same window,
		# so two simultaneous requests cannot both pass the capacity check
		booked = count_overlapping_appointments(
			self.scheduled_time,
			cint(settings.appointment_duration),
			exclude_appointment=self.name,
			for_update=True,
		)

		if booked >= cint(settings.number_of_agents):
			frappe.throw(_("Time slot is not available"))

	def before_insert(self):
		# Set status to "Unverified" for new Appointments.
		if self.created_through_portal:
			self.status = "Unverified"
			return

		self.link_customer_lead()

	def after_insert(self):
		if not self.created_through_portal and self.party:
			self.auto_assign()
			self.create_calendar_event()
			return

		# Send email to confirm
		self.send_confirmation_email()

	def on_update(self):
		# capture transitions before nested saves during materialization
		# refresh the before-save snapshot
		status_changed = self.has_value_changed("status")
		email_just_verified = bool(
			self.created_through_portal and self.email_verified
		) and self.has_value_changed("email_verified")

		self.link_auto_assign_and_create_calendar_event()

		if email_just_verified:
			self.send_appointment_confirmed_email()

		if status_changed:
			self.update_event_and_assignments_status()

	def on_trash(self):
		# the Event only references the party, not the appointment,
		# so it must be cleaned up explicitly
		if not self.calendar_event:
			return

		event = self.calendar_event
		self.db_set("calendar_event", None, update_modified=False)
		frappe.delete_doc("Event", event, ignore_permissions=True)

	def send_confirmation_email(self):
		self.send_email_to_customer(
			template="confirm_appointment",
			subject=_("Appointment Confirmation"),
			args={"link": self._get_verify_url(), "expiry_minutes": get_verification_link_expiry()},
		)
		frappe.msgprint(_("Please check your email to confirm the appointment."))

	def send_appointment_confirmed_email(self):
		self.send_email_to_customer(
			template="appointment_confirmed",
			subject=_("Appointment Confirmed"),
			args={"scheduled_time": frappe.utils.format_datetime(self.scheduled_time)},
			reference_doctype="Appointment",
			reference_name=self.name,
		)

	def send_email_to_customer(self, template, subject, args, **kwargs):
		frappe.sendmail(
			recipients=[self.customer_email],
			template=template,
			args={"full_name": self.customer_name, "site_url": frappe.utils.get_url(), **args},
			subject=subject,
			**kwargs,
		)

	def link_auto_assign_and_create_calendar_event(self):
		if self.is_new() or (self.created_through_portal and not self.email_verified):
			return

		if not self.calendar_event:
			# first materialization: link the party, assign an agent, create the event
			self.link_customer_lead()
			self.auto_assign()
			self.create_calendar_event()

		self.sync_calendar_event()

	def sync_calendar_event(self):
		if not self.calendar_event or not self.has_value_changed("scheduled_time"):
			return

		cal_event = frappe.get_doc("Event", self.calendar_event)
		cal_event.starts_on = self.scheduled_time
		cal_event.save(ignore_permissions=True)

	def update_event_and_assignments_status(self):
		"""Close or reopen the calendar event and assignments along with the appointment."""
		if self.status == "Unverified":
			return

		is_closed = self.status == "Closed"
		new_status = "Closed" if is_closed else "Open"

		if self.calendar_event:
			frappe.db.set_value("Event", self.calendar_event, "status", new_status)

		# only move ToDos between Open and Closed - never touch Cancelled ones
		todo_filters = {
			"reference_type": "Appointment",
			"reference_name": self.name,
			"status": "Open" if is_closed else "Closed",
		}
		frappe.db.set_value("ToDo", todo_filters, "status", new_status)

	def link_customer_lead(self):
		if not self.party:
			customer = self.find_party_by_email("Customer")
			self.appointment_with = "Customer" if customer else "Lead"
			self.party = customer or self.find_party_by_email("Lead")

		self.create_lead_and_link()

	def find_party_by_email(self, doctype):
		party = frappe.get_all(doctype, filters={"email_id": self.customer_email}, limit=1, pluck="name")
		return party[0] if party else None

	def create_lead_and_link(self):
		# Return if already linked
		if self.party:
			return

		lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": self.customer_name,
				"email_id": self.customer_email,
				"phone": self.customer_phone_number,
			}
		)

		if self.customer_details:
			lead.append(
				"notes",
				{"note": self.customer_details, "added_by": frappe.session.user, "added_on": now()},
			)

		self.party = lead.insert(ignore_permissions=True).name

	def auto_assign(self):
		if self._assign:
			return

		if existing_assignee := self.get_assignee_from_latest_opportunity():
			# assign to whoever handles the party's latest opportunity
			self.assign_agent(existing_assignee)
			return

		busy_agents = get_busy_agents(self.scheduled_time)
		for agent in _get_agents_sorted_by_asc_workload(getdate(self.scheduled_time)):
			if agent not in busy_agents:
				self.assign_agent(agent)
				break

	def get_assignee_from_latest_opportunity(self):
		if not self.party or not frappe.db.exists("Lead", self.party):
			return None

		opportunities = frappe.get_all(
			"Opportunity",
			filters={"party_name": self.party},
			fields=["_assign"],
			order_by="creation desc",
			limit=1,
		)
		assignees = opportunities and frappe.parse_json(opportunities[0]._assign or "[]")
		return assignees[0] if assignees else None

	def assign_agent(self, agent):
		if not frappe.has_permission(doc=self, user=agent):
			add_docshare(self.doctype, self.name, agent, flags={"ignore_share_permission": True})

		add_assignment({"doctype": self.doctype, "name": self.name, "assign_to": [agent]})

	def create_calendar_event(self):
		if self.calendar_event:
			return

		event = frappe.get_doc(
			{
				"doctype": "Event",
				"subject": f"Appointment with {self.customer_name}",
				"starts_on": self.scheduled_time,
				"status": "Open",
				"type": "Public",
				"send_reminder": cint(get_booking_settings().email_reminders),
				"event_participants": self.get_event_participants(),
			}
		).insert(ignore_permissions=True)

		self.calendar_event = event.name
		self.save(ignore_permissions=True)

	def get_event_participants(self):
		participants = [dict(reference_doctype=self.appointment_with, reference_docname=self.party)]

		if employee := _get_employee_from_user(self._assign):
			participants.append(dict(reference_doctype="Employee", reference_docname=employee.name))

		return participants

	def _get_verify_url(self):
		key = self.generate_verification_key()
		return get_url("/book_appointment/verify?" + urlencode({"key": key}))

	def generate_verification_key(self):
		# store only the hash; the raw key lives solely in the emailed link
		key = frappe.generate_hash()
		self.db_set("verification_token", sha256_hash(key), update_modified=False)
		return key


def get_booking_settings():
	return frappe.get_cached_doc("Appointment Booking Settings")


def is_appointment_scheduling_enabled():
	return bool(cint(get_booking_settings().enable_scheduling))


def get_verification_link_expiry():
	"""Verification link expiry window in minutes."""
	return cint(get_booking_settings().verification_link_expiry_duration)


def count_overlapping_appointments(
	scheduled_time, appointment_duration, exclude_appointment=None, for_update=False
):
	"""Count non-Closed appointments whose duration window overlaps `scheduled_time`.
	With `for_update`, the range stays locked until commit, serializing concurrent bookings."""
	# select the rows (not COUNT) so `for_update` stays valid: PostgreSQL
	# rejects `FOR UPDATE` combined with an aggregate function
	appointment = frappe.qb.DocType("Appointment")
	query = (
		frappe.qb.from_(appointment)
		.select(appointment.name)
		.where(appointment.scheduled_time > add_to_date(scheduled_time, minutes=-appointment_duration))
		.where(appointment.scheduled_time < add_to_date(scheduled_time, minutes=appointment_duration))
		.where(appointment.status != "Closed")
	)

	if exclude_appointment:
		query = query.where(appointment.name != exclude_appointment)

	if for_update:
		query = query.for_update()

	return len(query.run())


def handle_expired_unverified_appointments():
	"""Close or delete Unverified appointments whose verification link has expired."""
	expiry = get_verification_link_expiry()
	if not expiry:
		return

	cutoff = add_to_date(now_datetime(), minutes=-expiry)
	filters = {"status": "Unverified", "creation": ("<", cutoff)}
	action = get_booking_settings().action_for_expired_unverified_appointments or "Mark as Closed"

	if action == "Mark as Closed":
		frappe.db.set_value("Appointment", filters, "status", "Closed")
	elif action == "Delete Permanently":
		for name in frappe.get_all("Appointment", filters=filters, pluck="name"):
			frappe.delete_doc("Appointment", name, ignore_permissions=True)


def _get_agents_sorted_by_asc_workload(date):
	# count only the given day's assignments; scheduled_time is indexed so the
	# date range is resolved in SQL instead of scanning every appointment ever
	workload = Counter(agent.user for agent in get_booking_settings().agent_list)
	assigns = frappe.get_all(
		"Appointment",
		filters=[
			["_assign", "is", "set"],
			["scheduled_time", ">=", getdate(date)],
			["scheduled_time", "<", add_to_date(getdate(date), days=1)],
		],
		pluck="_assign",
	)

	for assign in assigns:
		assignees = frappe.parse_json((assign or "").strip() or "[]")
		if assignees and assignees[0] in workload:
			workload[assignees[0]] += 1

	return [agent for agent, _workload in reversed(workload.most_common())]


def get_busy_agents(scheduled_time):
	"""Agents already assigned to a non-Closed appointment overlapping `scheduled_time`."""
	duration = _get_appointment_duration()
	assigns = frappe.get_all(
		"Appointment",
		filters=[
			["scheduled_time", ">", add_to_date(scheduled_time, minutes=-duration)],
			["scheduled_time", "<", add_to_date(scheduled_time, minutes=duration)],
			["status", "!=", "Closed"],
		],
		pluck="_assign",
	)
	return {assignee for assign in assigns for assignee in frappe.parse_json(assign or "[]")}


def _check_agent_availability(agent_email, scheduled_time):
	return agent_email not in get_busy_agents(scheduled_time)


def get_booked_slot_times(from_time, to_time):
	"""scheduled_times of non-Closed appointments within (from_time, to_time), for slot availability."""
	return frappe.get_all(
		"Appointment",
		filters=[
			["scheduled_time", ">", from_time],
			["scheduled_time", "<", to_time],
			["status", "!=", "Closed"],
		],
		pluck="scheduled_time",
	)


def _get_appointment_duration():
	return cint(get_booking_settings().appointment_duration)


def _get_employee_from_user(user):
	employee_docname = frappe.db.get_value("Employee", {"user_id": user})
	return frappe.get_doc("Employee", employee_docname) if employee_docname else None
