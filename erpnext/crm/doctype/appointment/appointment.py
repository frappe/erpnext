# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from collections import Counter

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, getdate
from frappe.utils.verified_command import get_signed_params


class Appointment(Document):
	def before_insert(self):
		self.validate_slot_available()

	def after_insert(self):
		if self.lead:
			# Create Calendar event
			self.auto_assign()
			self.create_calendar_event()
		else:
			# Set status to unverified
			self.status = 'Unverified'
			# Send email to confirm
			self.send_confirmation_email()

	def on_change(self):
		# Sync Calendar
		if not self.calendar_event:
			return

		cal_event = frappe.get_doc('Event', self.calendar_event)
		cal_event.starts_on = self.scheduled_dt
		cal_event.save(ignore_permissions=True)

	def validate_slot_available(self):
		number_of_appointments_in_same_slot = self.count_appointments_in_same_slot()
		number_of_agents = frappe.db.get_single_value('Appointment Booking Settings', 'number_of_agents')
		if not number_of_agents == 0:
			if number_of_appointments_in_same_slot >= number_of_agents:
				frappe.throw('Time slot is not available')

	def count_appointments_in_same_slot(self):
		number_of_appointments_in_same_slot = frappe.db.count('Appointment', filters={'scheduled_dt': self.scheduled_dt})
		return number_of_appointments_in_same_slot

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

	def create_calendar_event(self):
		if self.calendar_event:
			return

		appointment_event = frappe.get_doc({
			'doctype': 'Event',
			'subject': ' '.join(['Appointment with', self.customer_name]),
			'starts_on': self.scheduled_dt,
			'status': 'Open',
			'type': 'Public',
			'send_reminder': frappe.db.get_single_value('Appointment Booking Settings', 'email_reminders'),
			'event_participants': [dict(reference_doctype='Lead', reference_docname=self.lead)]
		})

		employee = get_employee_from_user(self._assign)
		if employee:
			appointment_event.append('event_participants', dict(
				reference_doctype='Employee',
				reference_docname=employee.name))

		appointment_event.insert(ignore_permissions=True)

		self.calendar_event = appointment_event.name
		self.save(ignore_permissions=True)

	def send_confirmation_email(self):
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
		if email != self.customer_email:
			frappe.throw('Email verification failed.')

		self.create_lead_and_link(update=True)
		self.status = 'Open'
		self.auto_assign()
		self.create_calendar_event()

	def auto_assign(self):
		from frappe.desk.form.assign_to import add as add_assignemnt
		existing_assignee = self.get_assignee_from_latest_opportunity()
		if existing_assignee:
			# If the latest opportunity is assigned to someone
			# Assign the appointment to the same
			add_assignemnt({
				'doctype': self.doctype,
				'name': self.name,
				'assign_to': existing_assignee
			})
			return
		if self._assign:
			return

		available_agents = get_agents_sorted_by_asc_workload(getdate(self.scheduled_dt))

		for agent in available_agents:
			if check_agent_availability(agent, self.scheduled_dt):
				agent = agent[0]
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

		opporutnities = frappe.get_list('Opportunity', filters={'party_name': self.lead},
			ignore_permissions=True, order_by='creation desc')
		if not opporutnities:
			return None

		latest_opportunity = frappe.get_doc('Opportunity', opporutnities[0].name)
		assignee = latest_opportunity._assign
		if not assignee:
			return None

		assignee = frappe.parse_json(assignee)[0]
		return assignee


def get_agents_sorted_by_asc_workload(date):
	appointments = frappe.db.get_list('Appointment', fields='*')
	agent_list = get_agent_list_as_strings()
	if not appointments:
		return agent_list
	appointment_counter = Counter(agent_list)
	for appointment in appointments:
		assigned_to = frappe.parse_json(appointment._assign)
		if not assigned_to:
			continue
		if (assigned_to[0] in agent_list) and getdate(appointment.scheduled_dt) == date:
			appointment_counter[assigned_to[0]] += 1
	sorted_agent_list = appointment_counter.most_common()
	sorted_agent_list.reverse()
	return sorted_agent_list


def get_agent_list_as_strings():
	agent_list_as_strings = []
	agent_list = frappe.get_doc('Appointment Booking Settings').agent_list
	for agent in agent_list:
		agent_list_as_strings.append(agent.user)
	return agent_list_as_strings


def check_agent_availability(agent_email, scheduled_dt):
	appointemnts_at_scheduled_time = frappe.get_list(
		'Appointment', filters={'scheduled_dt': scheduled_dt})
	for appointment in appointemnts_at_scheduled_time:
		if appointment._assign == agent_email:
			return False
	return True


def get_employee_from_user(user):
	employee_docname = frappe.db.get_value('Employee', filters={'user_id': user})
	return employee_docname
