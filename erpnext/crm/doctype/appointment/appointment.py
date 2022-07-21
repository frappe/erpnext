# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
import datetime
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, getdate, get_time, get_datetime, combine_datetime, cint, format_datetime, formatdate
from frappe.utils.verified_command import get_signed_params
from erpnext.hr.doctype.employee.employee import get_employee_from_user
from frappe.desk.form.assign_to import add as add_assignemnt, clear as clear_assignments, close_all_assignments


class Appointment(Document):
	def validate(self):
		self.set_missing_values()
		if self.status in ['Open', 'Unconfirmed']:
			self.validate_timeslot_validity()
			self.validate_timeslot_availability()

	def on_update(self):
		self.auto_assign()
		self.auto_unassign()

		if self.calendar_event:
			self.sync_calendar_event()
		else:
			self.create_calendar_event(update=True)

	def set_missing_values(self):
		self.set_missing_duration()
		self.set_scheduled_date_time()

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

	def validate_timeslot_validity(self):
		if not self.appointment_type:
			return

		appointment_type_doc = frappe.get_cached_doc("Appointment Type", self.appointment_type)

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

	def create_lead_and_link(self, update=False):
		if self.lead:
			return

		lead = frappe.get_doc({
			'doctype': 'Lead',
			'lead_name': self.customer_name,
			'email_id': self.customer_email,
			'notes': self.customer_details,
			'phone': self.customer_phone_number,
		})
		lead.insert(ignore_permissions=True)

		self.lead = lead.name
		if update:
			self.db_set('lead', self.lead)

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
		if self.get('customer'):
			event_participants.append({"reference_doctype": "Customer", "reference_docname": self.customer})
		elif self.get('lead'):
			event_participants.append({"reference_doctype": "Lead", "reference_docname": self.lead})

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
		if self.status != "Unconfirmed":
			return
		if not self.customer_email:
			return

		verify_url = self.get_verify_url()
		template = 'confirm_appointment'
		args = {
			"link": verify_url,
			"site_url": frappe.utils.get_url(),
			"full_name": self.customer_name,
		}

		frappe.sendmail(recipients=[self.customer_email],
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
			'email': self.customer_email,
			'appointment': self.name
		}
		return get_url(verify_route + '?' + get_signed_params(params))

	def set_verified(self, email):
		if self.status not in ['Open', 'Unconfirmed']:
			frappe.throw(_("Appointment is {0}").format(self.status))
		if email != self.customer_email:
			frappe.throw(_('Email verification failed.'))

		self.db_set('status', 'Open')
		self.create_lead_and_link(update=True)
		self.create_calendar_event(update=True)
		self.auto_assign()

	def auto_unassign(self):
		if self.status == "Closed":
			close_all_assignments(self.doctype, self.name)
		elif self.status in ["Cancelled", "Rescheduled"]:
			clear_assignments(self.doctype, self.name)

	def auto_assign(self):
		if self.status != 'Open':
			return
		if self._assign:
			return
		if not self.appointment_type:
			return

		appointment_type_doc = frappe.get_cached_doc("Appointment Type", self.appointment_type)
		if not appointment_type_doc.auto_assign_agent:
			return

		existing_assignee = self.get_assignee_from_latest_opportunity()
		if existing_assignee:
			add_assignemnt({
				'doctype': self.doctype,
				'name': self.name,
				'assign_to': existing_assignee
			})
			return

		available_agents = get_agents_sorted_by_asc_workload(getdate(self.scheduled_dt), self.appointment_type)

		for agent in available_agents:
			if check_agent_availability(agent, self.scheduled_dt, self.end_dt):
				add_assignemnt({
					'doctype': self.doctype,
					'name': self.name,
					'assign_to': agent
				})
				break

	def get_assignee_from_latest_opportunity(self):
		if not self.lead:
			return None
		if not frappe.db.exists('Lead', self.lead):
			return None

		latest_opportunity = frappe.get_all('Opportunity', filters={'opportunity_from': 'Lead', 'party_name': self.lead},
			order_by='creation desc', fields=['name', '_assign'])
		if not latest_opportunity:
			return None

		latest_opportunity = latest_opportunity[0]
		assignee = latest_opportunity._assign
		if not assignee:
			return None

		assignee = frappe.parse_json(assignee)[0]
		return assignee

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


def get_agents_sorted_by_asc_workload(date, appointment_type):
	date = getdate(date)

	agents = get_agents_list(appointment_type)
	if not agents:
		return []

	appointments = frappe.get_all('Appointment', fields=['name', '_assign'],
		filters={'scheduled_date': date, 'status': ['in', ['Open', 'Closed']]})
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
	if not scheduled_date:
		frappe.throw(_("Schedule Date not provided"))
	if not appointment_type:
		frappe.throw(_("Appointment Type not provided"))

	scheduled_date = getdate(scheduled_date)
	appointment_type_doc = frappe.get_cached_doc("Appointment Type", appointment_type)

	out = frappe._dict({
		'holiday': appointment_type_doc.is_holiday(scheduled_date, company=company),
		'timeslots': []
	})

	timeslots = appointment_type_doc.get_timeslots(scheduled_date)
	no_of_agents = cint(appointment_type_doc.number_of_agents)

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
		where status = 'Open' and appointment_type = %(appointment_type)s
			and %(start_dt)s < end_dt AND %(end_dt)s > scheduled_dt {0}
	""".format(exclude_condition), {
		'start_dt': start_dt,
		'end_dt': end_dt,
		'appointment_type': appointment_type,
		'appointment': appointment
	}, as_dict=1)

	return appointments
