# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
import datetime
from frappe import _
from erpnext.controllers.status_updater import StatusUpdater
from frappe.utils import cint, today, getdate, get_time, get_datetime, combine_datetime, date_diff,\
	format_datetime, formatdate, get_url, now_datetime, add_days, clean_whitespace
from frappe.utils.verified_command import get_signed_params
from erpnext.hr.doctype.employee.employee import get_employee_from_user
from frappe.desk.form.assign_to import add as add_assignment, clear as clear_assignments, close_all_assignments
from six import string_types
from frappe.contacts.doctype.address.address import get_address_display, get_default_address
from frappe.contacts.doctype.contact.contact import get_contact_details, get_default_contact, get_all_contact_nos
from erpnext.crm.doctype.lead.lead import _get_lead_contact_details, get_customer_from_lead
from erpnext.stock.get_item_details import get_applies_to_details
from erpnext.vehicles.doctype.vehicle_log.vehicle_log import get_customer_vehicle_selector_data
from frappe.core.doctype.sms_settings.sms_settings import enqueue_template_sms
from frappe.core.doctype.notification_count.notification_count import clear_notification_count
from frappe.model.mapper import get_mapped_doc
import json


force_fields = ['customer_name', 'tax_id', 'tax_cnic', 'tax_strn',
	'address_display', 'contact_display', 'contact_email', 'secondary_contact_display',
	"vehicle_chassis_no", "vehicle_engine_no", "vehicle_license_plate", "vehicle_unregistered",
	"vehicle_color", "applies_to_item", "applies_to_item_name", "applies_to_variant_of", "applies_to_variant_of_name"
]


class Appointment(StatusUpdater):
	def get_feed(self):
		return _("For {0}").format(self.get("customer_name") or self.get('party_name'))

	def onload(self):
		if self.docstatus == 0:
			self.set_missing_values()
		elif self.docstatus == 1:
			self.set_onload('disallow_on_submit', self.get_disallow_on_submit_fields())

		self.set_onload('customer', self.get_customer())
		self.set_onload('appointment_timeslots_data', get_appointment_timeslots(self.scheduled_date, self.appointment_type,
			company=self.company))
		self.set_onload('contact_nos', get_all_contact_nos(self.appointment_for, self.party_name))

		self.set_can_notify_onload()

		if self.meta.has_field('applies_to_vehicle'):
			self.set_onload('customer_vehicle_selector_data', get_customer_vehicle_selector_data(self.get_customer(),
				self.get('applies_to_vehicle')))

	def validate(self):
		self.set_missing_values()
		self.validate_previous_appointment()
		self.validate_timeslot_validity()
		self.validate_timeslot_availability()
		self.clean_remarks()
		self.set_status()

	def before_insert(self):
		clear_notification_count(self)

	def before_update_after_submit(self):
		if self.status not in ["Closed", "Rescheduled"]:
			self.set_customer_details()
			self.set_applies_to_details()

		self.clean_remarks()
		self.set_status()
		self.get_disallow_on_submit_fields()

	def before_submit(self):
		self.confirmation_dt = now_datetime()

	def on_submit(self):
		self.update_previous_appointment()
		self.auto_assign()
		self.create_calendar_event(update=True)
		self.send_appointment_confirmation_notification()

	def on_cancel(self):
		self.db_set('status', 'Cancelled')
		self.validate_on_cancel()
		self.update_previous_appointment()
		self.auto_unassign()
		self.send_appointment_cancellation_notification()

	def get_disallow_on_submit_fields(self):
		if self.status in ["Closed", "Rescheduled"]:
			self.flags.disallow_on_submit = self.get_fields_for_disallow_on_submit(['remarks'])

		return self.flags.disallow_on_submit or []

	def get_customer(self, throw=False):
		if self.appointment_for == "Customer":
			return self.party_name
		elif self.appointment_for == "Lead":
			return get_customer_from_lead(self.party_name, throw=throw)
		else:
			return None

	def set_missing_values(self):
		self.set_previous_appointment_details()
		self.set_missing_duration()
		self.set_scheduled_date_time()
		self.set_customer_details()
		self.set_applies_to_details()

	def set_previous_appointment_details(self):
		if self.previous_appointment:
			self.previous_appointment_dt = frappe.db.get_value("Appointment", self.previous_appointment, "scheduled_dt")

	def set_missing_duration(self):
		if self.get('appointment_type'):
			appointment_type_doc = frappe.get_cached_doc("Appointment Type", self.appointment_type)
			if cint(self.appointment_duration) <= 0:
				self.appointment_duration = cint(appointment_type_doc.appointment_duration)

	def set_scheduled_date_time(self):
		if not self.scheduled_dt and self.scheduled_date and self.scheduled_time:
			self.scheduled_dt = combine_datetime(self.scheduled_date, self.scheduled_time)

		if self.scheduled_dt:
			self.scheduled_dt = get_datetime(self.scheduled_dt)
			self.scheduled_date = getdate(self.scheduled_dt)
			self.scheduled_time = get_time(self.scheduled_dt)
		else:
			self.scheduled_date = None
			self.scheduled_time = None

		self.appointment_duration = cint(self.appointment_duration)
		if self.scheduled_dt and self.appointment_duration > 0:
			duration = datetime.timedelta(minutes=self.appointment_duration)
			self.end_dt = self.scheduled_dt + duration
		else:
			self.end_dt = self.scheduled_dt

		if self.scheduled_date:
			self.scheduled_day_of_week = formatdate(self.scheduled_date, "EEEE")
		else:
			self.scheduled_day_of_week = None

	def set_customer_details(self):
		customer_details = get_customer_details(self.as_dict())
		for k, v in customer_details.items():
			if self.meta.has_field(k) and (not self.get(k) or k in force_fields):
				self.set(k, v)

	def set_applies_to_details(self):
		args = self.as_dict()
		applies_to_details = get_applies_to_details(args, for_validate=True)

		for k, v in applies_to_details.items():
			if self.meta.has_field(k) and not self.get(k) or k in force_fields:
				self.set(k, v)

	def clean_remarks(self):
		fields = ['remarks']

		if self.status not in ["Closed", "Rescheduled"]:
			fields.append('voice_of_customer')

		for f in fields:
			if self.meta.has_field(f):
				self.set(f, clean_whitespace(self.get(f)))

	def validate_timeslot_validity(self):
		if not self.appointment_type:
			return

		appointment_type_doc = frappe.get_cached_doc("Appointment Type", self.appointment_type)

		# check if in past
		if getdate(self.scheduled_dt) < getdate(today()):
			frappe.msgprint(_("Warning: Scheduled Date {0} is in the past")
				.format(frappe.bold(frappe.format(getdate(self.scheduled_date)))), indicator="orange")

		advance_days = date_diff(getdate(self.scheduled_dt), today())
		if cint(appointment_type_doc.advance_booking_days) and advance_days > cint(appointment_type_doc.advance_booking_days):
			frappe.msgprint(_("Scheduled Date {0} is {1} days in advance")
				.format(frappe.bold(frappe.format(getdate(self.scheduled_date))), frappe.bold(advance_days)),
				raise_exception=appointment_type_doc.validate_availability)

		# check if in valid timeslot
		if not appointment_type_doc.is_in_timeslot(self.scheduled_dt, self.end_dt):
			timeslot_str = self.get_timeslot_str()
			frappe.msgprint(_('{0} is not a valid available time slot for appointment type {1}')
				.format(timeslot_str, self.appointment_type), raise_exception=appointment_type_doc.validate_availability)

	def validate_timeslot_availability(self):
		if not self.appointment_type:
			return

		appointment_type_doc = frappe.get_cached_doc("Appointment Type", self.appointment_type)

		# check if holiday
		holiday = appointment_type_doc.is_holiday(self.scheduled_dt, self.company)
		if holiday:
			frappe.msgprint(_("{0} is a holiday: {1}")
				.format(frappe.bold(formatdate(self.scheduled_dt, "EEEE, d MMMM, Y")), holiday),
				raise_exception=appointment_type_doc.validate_availability)

		# check if already booked
		appointments_in_same_slot = count_appointments_in_same_slot(self.scheduled_dt, self.end_dt,
			self.appointment_type, appointment=self.name if not self.is_new() else None)
		no_of_agents = cint(appointment_type_doc.number_of_agents)

		if no_of_agents and appointments_in_same_slot >= no_of_agents:
			timeslot_str = self.get_timeslot_str()
			frappe.msgprint(_('Time slot {0} is already booked by {1} other appointments for appointment type {2}')
				.format(timeslot_str, frappe.bold(appointments_in_same_slot), self.appointment_type),
				raise_exception=appointment_type_doc.validate_availability)

	def validate_previous_appointment(self):
		if self.previous_appointment:
			previous_appointment = frappe.db.get_value("Appointment", self.previous_appointment,
				['docstatus', 'status'], as_dict=1)
			if not previous_appointment:
				frappe.throw(_("Previous Appointment {0} does not exist").format(self.previous_appointment))

			if previous_appointment.docstatus == 0:
				frappe.throw(_("Previous {0} is not submitted")
					.format(frappe.get_desk_link("Appointment", self.previous_appointment)))
			if previous_appointment.docstatus == 2:
				frappe.throw(_("Previous {0} is cancelled")
					.format(frappe.get_desk_link("Appointment", self.previous_appointment)))
			if previous_appointment.status not in ["Open", "Missed"]:
				frappe.throw(_("Previous {0} is {1}. Only Open and Missed appointments can be resheduled")
					.format(frappe.get_desk_link("Appointment", self.previous_appointment)), previous_appointment.status)

	def update_previous_appointment(self):
		if self.previous_appointment:
			doc = frappe.get_doc("Appointment", self.previous_appointment)
			doc.set_status(update=True)

			if self.docstatus == 2:
				doc.validate_timeslot_availability()

			doc.auto_unassign()
			doc.notify_update()

	def create_lead_and_link(self):
		if self.party_name:
			return

		lead = frappe.get_doc({
			'doctype': 'Lead',
			'lead_name': self.customer_name,
			'email_id': self.contact_email,
			'notes': self.description,
			'mobile_no': self.contact_mobile,
		})
		lead.insert(ignore_permissions=True)

		self.appointment_for = "Lead"
		self.party_name = lead.name

	def create_calendar_event(self, update=False):
		if self.status != "Open":
			return
		if self.calendar_event:
			return
		if not self.appointment_type:
			return

		appointment_type_doc = frappe.get_cached_doc("Appointment Type", self.appointment_type)
		if not appointment_type_doc.create_calendar_event:
			return

		event_participants = []
		if self.get('appointment_for') and self.get('party_name'):
			event_participants.append({"reference_doctype": self.appointment_for, "reference_docname": self.party_name})

		appointment_event = frappe.get_doc({
			'doctype': 'Event',
			'subject': ' '.join(['Appointment with', self.customer_name]),
			'starts_on': self.scheduled_dt,
			'ends_on': self.end_dt,
			'status': 'Open',
			'type': 'Public',
			'send_reminder': appointment_type_doc.email_reminders,
			'event_participants': event_participants
		})

		employee = get_employee_from_user(self._assign)
		if employee:
			appointment_event.append('event_participants', dict(
				reference_doctype='Employee',
				reference_docname=employee.name))

		appointment_event.insert(ignore_permissions=True)

		self.calendar_event = appointment_event.name
		if update:
			self.db_set('calendar_event', self.calendar_event)

	def sync_calendar_event(self):
		if not self.calendar_event:
			return

		cal_event = frappe.get_doc('Event', self.calendar_event)
		cal_event.starts_on = self.scheduled_dt
		cal_event.end_on = self.end_dt
		cal_event.save(ignore_permissions=True)

	def send_confirmation_email(self):
		if self.docstatus != 0:
			return
		if not self.contact_email:
			return

		verify_url = self.get_verify_url()
		template = 'confirm_appointment'
		args = {
			"link": verify_url,
			"site_url": frappe.utils.get_url(),
			"full_name": self.customer_name,
		}

		frappe.sendmail(recipients=[self.contact_email],
			template=template,
			args=args,
			subject=_('Appointment Confirmation'))

		if frappe.session.user == "Guest":
			frappe.msgprint('Please check your email to confirm the appointment')
		else:
			frappe.msgprint('Appointment was created. But no lead was found. Please check the email to confirm')

	def get_verify_url(self):
		verify_route = '/book_appointment/verify'
		params = {
			'email': self.contact_email,
			'appointment': self.name
		}
		return get_url(verify_route + '?' + get_signed_params(params))

	def set_verified(self, email):
		if self.docstatus != 0:
			frappe.throw(_("Appointment is already {0}").format(self.status))
		if email != self.contact_email:
			frappe.throw(_('Email verification failed.'))

		self.submit()

	def auto_unassign(self):
		if self.docstatus == 2 or self.status == "Rescheduled":
			clear_assignments(self.doctype, self.name)
		elif self.status == "Closed":
			close_all_assignments(self.doctype, self.name)

	def auto_assign(self):
		if self.status != 'Open':
			return
		if self.get('_assign'):
			return
		if not self.appointment_type:
			return

		appointment_type_doc = frappe.get_cached_doc("Appointment Type", self.appointment_type)
		if not appointment_type_doc.auto_assign_agent:
			return

		existing_assignee = self.get_assignee_from_latest_opportunity()
		if existing_assignee:
			add_assignment({
				'doctype': self.doctype,
				'name': self.name,
				'assign_to': existing_assignee
			})
			return

		available_agents = get_agents_sorted_by_asc_workload(getdate(self.scheduled_dt), self.appointment_type)

		for agent in available_agents:
			if check_agent_availability(agent, self.scheduled_dt, self.end_dt):
				add_assignment({
					'doctype': self.doctype,
					'name': self.name,
					'assign_to': agent
				})
				break

	def get_assignee_from_latest_opportunity(self):
		if not self.appointment_for or not self.party_name:
			return None

		latest_opportunity = frappe.get_all('Opportunity',
			filters={'opportunity_from': self.appointment_for, 'party_name': self.party_name},
			order_by='creation desc', fields=['name', '_assign'])
		if not latest_opportunity:
			return None

		latest_opportunity = latest_opportunity[0]
		assignee = latest_opportunity._assign
		if not assignee:
			return None

		assignee = frappe.parse_json(assignee)[0]
		return assignee

	def set_status(self, update=False, status=None, update_modified=True):
		previous_status = self.status
		previous_is_closed = self.is_closed

		if self.docstatus == 0:
			self.status = "Draft"

		elif self.docstatus == 1:
			if status == "Open":
				self.is_closed = 0
				self.is_missed = 0
			elif status == "Closed":
				self.is_closed = 1
				self.is_missed = 0
			elif status == "Missed":
				self.is_missed = 1
				self.is_closed = 0

			# Submitted or cancelled rescheduled appointment
			is_rescheduled = frappe.get_all("Appointment", filters={'previous_appointment': self.name, 'docstatus': ['>', 0]})

			if is_rescheduled:
				self.status = "Rescheduled"
			elif self.is_closed or self.get_linked_project():
				self.status = "Closed"
			elif self.is_missed or getdate(today()) > getdate(self.scheduled_date):
				self.status = "Missed"
			else:
				self.status = "Open"

		else:
			self.status = "Cancelled"

		self.add_status_comment(previous_status)

		if update:
			if previous_status != self.status or previous_is_closed != self.is_closed:
				self.db_set({
					'status': self.status,
					'is_closed': self.is_closed,
				}, update_modified=update_modified)

	def get_linked_project(self):
		return frappe.db.get_value("Project", {'appointment': self.name})

	def validate_on_cancel(self):
		project = self.get_linked_project()
		if project:
			frappe.throw(_("Cannot cancel appointment because it is closed by {0}")
				.format(frappe.get_desk_link("Project", project)))

	def get_timeslot_str(self):
		if self.scheduled_dt == self.end_dt:
			timeslot_str = frappe.bold(self.get_formatted_dt())
		elif getdate(self.scheduled_dt) == getdate(self.end_dt):
			timeslot_str = _("{0} {1} till {2}").format(
				frappe.bold(format_datetime(self.scheduled_dt, "EEEE, d MMMM, Y")),
				frappe.bold(format_datetime(self.scheduled_dt, "hh:mm:ss a")),
				frappe.bold(format_datetime(self.end_dt, "hh:mm:ss a"))
			)
		else:
			timeslot_str = _("{0} till {1}").format(
				frappe.bold(self.get_formatted('scheduled_dt')),
				frappe.bold(self.get_formatted('end_dt'))
			)

		return timeslot_str

	def get_formatted_dt(self, dt=None):
		if not dt:
			dt = self.scheduled_dt

		if dt:
			return format_datetime(self.scheduled_dt, "EEEE, d MMMM, Y hh:mm:ss a")
		else:
			return ""

	def get_sms_args(self, notification_type=None):
		return frappe._dict({
			'receiver_list': [self.contact_mobile],
			'party_doctype': self.appointment_for,
			'party': self.party_name
		})

	def set_can_notify_onload(self):
		notification_types = [
			'Appointment Confirmation',
			'Appointment Reminder',
			'Appointment Cancellation',
		]

		can_notify = frappe._dict()
		for notification_type in notification_types:
			can_notify[notification_type] = self.validate_notification(notification_type, throw=False)

		self.set_onload('can_notify', can_notify)

	def validate_notification(self, notification_type=None, throw=False):
		if not notification_type:
			if throw:
				frappe.throw(_("Notification Type is mandatory"))
			return False

		if notification_type == 'Appointment Cancellation':
			# Must be cancelled
			if self.docstatus != 2:
				if throw:
					frappe.throw(_("Cannot send Appointment Cancellation notification because Appointment is not cancelled"))
				return False
		elif notification_type != 'Custom Message':
			# Must be submitted
			if self.docstatus != 1:
				if throw:
					frappe.throw(_("Cannot send notification because Appointment is not submitted"))
				return False

		# Must be Open
		if notification_type in ("Appointment Confirmation", "Appointment Reminder"):
			if self.status != "Open":
				if throw:
					frappe.throw(_("Cannot send {0} notification because Appointment status is not 'Open'")
						.format(notification_type))
				return False

		# Appointment Start Date/Time is in the past or End Date/Time if cancellation
		if notification_type in ("Appointment Confirmation", "Appointment Reminder", "Appointment Cancellation"):
			appointment_dt = self.end_dt if "Appointment Cancellation" else self.scheduled_dt
			appointment_dt = get_datetime(appointment_dt or self.scheduled_dt)

			if appointment_dt <= now_datetime():
				if throw:
					frappe.throw(_("Cannot send {0} notification after Appointment Time has passed")
						.format(notification_type))
				return False

		return True

	def send_appointment_confirmation_notification(self):
		if self.docstatus == 1:
			enqueue_template_sms(self, notification_type="Appointment Confirmation")

	def send_appointment_cancellation_notification(self):
		if self.docstatus == 2:
			enqueue_template_sms(self, notification_type="Appointment Cancellation")

	def send_appointment_reminder_notification(self):
		enqueue_template_sms(self, notification_type="Appointment Reminder")


def get_agents_sorted_by_asc_workload(date, appointment_type):
	date = getdate(date)

	agents = get_agents_list(appointment_type)
	if not agents:
		return []

	appointments = frappe.get_all('Appointment', fields=['name', '_assign'],
		filters={'scheduled_date': date, 'docstatus': 1, 'status': ['!=', 'Rescheduled']})
	if not appointments:
		return agents

	agent_booked_dict = {agent: 0 for agent in agents}

	for appointment in appointments:
		assigned_to = frappe.parse_json(appointment._assign or '[]')
		if not assigned_to:
			continue

		assigned_to = assigned_to[0]
		if assigned_to not in agents:
			continue

		agent_booked_dict[assigned_to] += 1

	agent_booked_list = list(agent_booked_dict.items())
	sorted_agent_booked_list = sorted(agent_booked_list, key=lambda d: d[1])
	return [d[0] for d in sorted_agent_booked_list]


def get_agents_list(appointment_type):
	if not appointment_type:
		return []

	appointment_type_doc = frappe.get_cached_doc('Appointment Type')
	return appointment_type_doc.get_agents()


def check_agent_availability(agent, scheduled_dt, end_dt):
	appointments = get_appointments_in_same_slot(scheduled_dt, end_dt)
	for appointment in appointments:
		assignments = frappe.parse_json(appointment._assign or '[]')
		if agent in assignments:
			return False

	return True


@frappe.whitelist()
def get_appointment_timeslots(scheduled_date, appointment_type, appointment=None, company=None):
	out = frappe._dict({
		'holiday': None,
		'timeslots': []
	})

	if not scheduled_date or not appointment_type:
		return out

	scheduled_date = getdate(scheduled_date)
	appointment_type_doc = frappe.get_cached_doc("Appointment Type", appointment_type)

	out.holiday = appointment_type_doc.is_holiday(scheduled_date, company=company)

	timeslots = appointment_type_doc.get_timeslots(scheduled_date)
	no_of_agents = cint(appointment_type_doc.number_of_agents)

	if timeslots:
		for timeslot_start, timeslot_end in timeslots:
			appointments_in_same_slots = count_appointments_in_same_slot(timeslot_start, timeslot_end, appointment_type,
				appointment)

			timeslot_data = {
				'timeslot_start': timeslot_start,
				'timeslot_end': timeslot_end,
				'timeslot_duration': round((timeslot_end - timeslot_start) / datetime.timedelta(minutes=1)),
				'number_of_agents': no_of_agents,
				'booked': appointments_in_same_slots,
				'available': max(0, no_of_agents - appointments_in_same_slots)
			}
			out.timeslots.append(timeslot_data)

	elif timeslots is None:
		out.timeslots = None

	return out


def count_appointments_in_same_slot(start_dt, end_dt, appointment_type, appointment=None):
	appointments = get_appointments_in_same_slot(start_dt, end_dt, appointment_type, appointment=appointment)
	return len(appointments) if appointments else 0


def get_appointments_in_same_slot(start_dt, end_dt, appointment_type, appointment=None):
	start_dt = get_datetime(start_dt)
	end_dt = get_datetime(end_dt)

	exclude_condition = ""
	if appointment:
		exclude_condition = "and name != %(appointment)s"

	appointments = frappe.db.sql("""
		select name, _assign
		from `tabAppointment`
		where docstatus = 1 and status != 'Rescheduled' and appointment_type = %(appointment_type)s
			and %(start_dt)s < end_dt AND %(end_dt)s > scheduled_dt {0}
	""".format(exclude_condition), {
		'start_dt': start_dt,
		'end_dt': end_dt,
		'appointment_type': appointment_type,
		'appointment': appointment
	}, as_dict=1)

	return appointments


def auto_mark_missed():
	auto_mark_missed_days = cint(frappe.get_cached_value("Appointment Booking Settings", None, "auto_mark_missed_days"))
	if auto_mark_missed_days > 0:
		frappe.db.sql("""
			update `tabAppointment`
			set status = 'Missed'
			where docstatus = 1 and status = 'Open' and DATEDIFF(CURDATE(), scheduled_date) >= %s
		""", auto_mark_missed_days)


@frappe.whitelist()
def get_customer_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	if not args.appointment_for or not args.party_name:
		frappe.throw(_("Party is mandatory"))

	if args.appointment_for not in ['Customer', 'Lead']:
		frappe.throw(_("Appointment For must be either Customer or Lead"))

	party = frappe.get_cached_doc(args.appointment_for, args.party_name)

	# Customer Name
	if party.doctype == "Lead":
		out.customer_name = party.company_name or party.lead_name
	else:
		out.customer_name = party.customer_name

	# Tax IDs
	out.tax_id = party.get('tax_id')
	out.tax_cnic = party.get('tax_cnic')
	out.tax_strn = party.get('tax_strn')

	# Address
	out.customer_address = args.customer_address or get_default_address(party.doctype, party.name)
	out.address_display = get_address_display(out.customer_address)

	# Contact
	out.contact_person = args.contact_person or get_default_contact(party.doctype, party.name)
	if party.doctype == "Lead" and not out.contact_person:
		out.update(_get_lead_contact_details(party))
	else:
		out.update(get_contact_details(out.contact_person))

	out.secondary_contact_person = args.secondary_contact_person
	secondary_contact_details = get_contact_details(out.secondary_contact_person)
	secondary_contact_details = {"secondary_" + k: v for k, v in secondary_contact_details.items()}
	out.update(secondary_contact_details)

	out.contact_nos = get_all_contact_nos(party.doctype, party.name)

	return out


@frappe.whitelist()
def get_project(source_name, target_doc=None):
	def set_missing_values(source, target):
		customer = source.get_customer(throw=True)
		if customer:
			target.customer = customer
			target.contact_mobile = source.get('contact_mobile')
			target.contact_mobile_2 = source.get('contact_mobile_2')
			target.contact_phone = source.get('contact_phone')

		if target.applies_to_item and frappe.get_cached_value("Item", target.applies_to_item, "has_variants"):
			target.applies_to_item = None
			target.applies_to_variant_of = None

		target.run_method("set_missing_values")

	doclist = get_mapped_doc("Appointment", source_name, {
		"Appointment": {
			"doctype": "Project",
			"field_map": {
				"name": "appointment",
				"scheduled_dt": "appointment_dt",
				"voice_of_customer": "project_name",
				"description": "description",
				"applies_to_vehicle": "applies_to_vehicle",
			}
		}
	}, target_doc, set_missing_values)

	return doclist


@frappe.whitelist()
def get_rescheduled_appointment(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.run_method("set_missing_values")

	doclist = get_mapped_doc("Appointment", source_name, {
		"Appointment": {
			"doctype": "Appointment",
			"field_no_map": [
				'scheduled_date',
				'scheduled_time',
				'scheduled_day_of_week',
				'scheduled_dt',
				'end_dt',
			],
			"field_map": {
				"name": "previous_appointment",
				"scheduled_dt": "previous_appointment_dt",
				"appointment_duration": "appointment_duration",
				"appointment_type": "appointment_type",
				"appointment_for": "appointment_for",
				"party_name": "party_name",
				"contact_person": "contact_person",
				"customer_address": "customer_address",
				"applies_to_vehicle": "applies_to_vehicle",
				"voice_of_customer": "voice_of_customer",
				"description": "description",
			}
		}
	}, target_doc, set_missing_values)

	return doclist


@frappe.whitelist()
def update_status(appointment, status):
	doc = frappe.get_doc("Appointment", appointment)
	doc.check_permission('write')
	doc.set_status(update=True, status=status)
	doc.auto_unassign()
	doc.notify_update()


def send_appointment_reminder_notifications():
	if not automated_reminder_enabled():
		return

	# Do not send until reminder scheduled time has passed
	now_dt = now_datetime()
	reminder_date = getdate(now_dt)
	reminder_dt = get_appointment_reminders_scheduled_time(reminder_date)
	if now_dt < reminder_dt:
		return

	appointments_to_remind = get_appointments_for_reminder_notification(reminder_date)

	for name in appointments_to_remind:
		doc = frappe.get_doc("Appointment", name)
		doc.send_appointment_reminder_notification()


def automated_reminder_enabled():
	from frappe.core.doctype.sms_settings.sms_settings import is_automated_sms_enabled
	from frappe.core.doctype.sms_template.sms_template import has_automated_sms_template

	if is_automated_sms_enabled() and has_automated_sms_template("Appointment", "Appointment Reminder"):
		return True
	else:
		return False


def get_appointments_for_reminder_notification(reminder_date=None):
	appointment_settings = frappe.get_cached_doc("Appointment Booking Settings", None)

	now_dt = now_datetime()
	reminder_date = getdate(reminder_date)
	reminder_dt = get_appointment_reminders_scheduled_time(reminder_date)

	remind_days_before = cint(appointment_settings.appointment_reminder_days_before)
	if remind_days_before < 0:
		remind_days_before = 0

	appointment_reminder_confirmation_hours = cint(appointment_settings.appointment_reminder_confirmation_hours)
	if appointment_reminder_confirmation_hours < 0:
		appointment_reminder_confirmation_hours = 0

	appointment_date = add_days(reminder_date, remind_days_before)

	appointments_to_remind = frappe.db.sql_list("""
		select a.name
		from `tabAppointment` a
		left join `tabNotification Count` n on n.parenttype = 'Appointment' and n.parent = a.name
			and n.notification_type = 'Appointment Reminder' and n.notification_medium = 'SMS'
		where a.docstatus = 1
			and a.status = 'Open'
			and a.scheduled_date = %(appointment_date)s
			and %(reminder_dt)s < a.scheduled_dt
			and %(now_dt)s < a.scheduled_dt
			and TIMESTAMPDIFF(MINUTE, a.confirmation_dt, %(reminder_dt)s) >= %(required_minutes)s
			and n.last_scheduled_dt is null
			and (n.last_sent_dt is null or DATE(n.last_sent_dt) != %(reminder_date)s)
	""", {
		'appointment_date': appointment_date,
		'reminder_dt': reminder_dt,
		'reminder_date': reminder_date,
		'now_dt': now_dt,
		'required_minutes': appointment_reminder_confirmation_hours * 60,
	})

	return appointments_to_remind


def get_appointment_reminders_scheduled_time(reminder_date=None):
	appointment_settings = frappe.get_cached_doc("Appointment Booking Settings", None)

	reminder_date = getdate(reminder_date)
	reminder_time = appointment_settings.appointment_reminder_time or get_time("00:00:00")
	reminder_dt = combine_datetime(reminder_date, reminder_time)

	return reminder_dt


def get_reminder_date_from_appointment_date(appointment_date):
	appointment_settings = frappe.get_cached_doc("Appointment Booking Settings", None)

	appointment_date = getdate(appointment_date)

	remind_days_before = cint(appointment_settings.appointment_reminder_days_before)
	if remind_days_before < 0:
		remind_days_before = 0

	reminder_date = add_days(appointment_date, -remind_days_before)
	return reminder_date


@frappe.whitelist()
def get_events(start, end, filters=None):
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Appointment", filters)

	data = frappe.db.sql("""
		select
			`tabAppointment`.name, `tabAppointment`.customer_name, `tabAppointment`.status,
			`tabAppointment`.scheduled_dt, `tabAppointment`.end_dt, `tabAppointment`.status
		from
			`tabAppointment`
		where ifnull(`tabAppointment`.scheduled_dt, '0000-00-00') != '0000-00-00'
			and `tabAppointment`.scheduled_dt between %(start)s and %(end)s
			and `tabAppointment`.docstatus < 2
			{conditions}
		""".format(conditions=conditions), {
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})

	return data
