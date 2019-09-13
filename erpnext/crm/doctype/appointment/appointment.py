# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from collections import Counter
from datetime import timedelta
import frappe
from frappe.model.document import Document
from frappe.desk.form.assign_to import add as add_assignemnt


def _get_agents_sorted_by_asc_workload():
	appointments = frappe.db.get_list('Appointment', fields='*')
	# Handle case where no appointments are created
	appointment_counter = Counter()
	if not appointments:
		return frappe.get_doc('Appointment Booking Settings').agent_list
	for appointment in appointments:
		if appointment._assign == '[]' or not appointment._assign:
			continue
		appointment_counter[appointment._assign] += 1
	sorted_agent_list = appointment_counter.most_common()
	sorted_agent_list.reverse()
	return sorted_agent_list

def _check_agent_availability(agent_email,scheduled_time):
	appointemnts_at_scheduled_time = frappe.get_list('Appointment', filters={'scheduled_time':scheduled_time})
	for appointment in appointemnts_at_scheduled_time:
		if appointment._assign == agent_email:
			return False
	return True

def _get_employee_from_user(user):
	return frappe.get_list('Employee', fields='*',filters={'user_id':user})

class Appointment(Document):
	def validate(self):
		number_of_appointments_in_same_slot = frappe.db.count('Appointment',filters={'scheduled_time':self.scheduled_time})
		settings = frappe.get_doc('Appointment Booking Settings')
		if(number_of_appointments_in_same_slot >= settings.number_of_agents):
			frappe.throw('Time slot is not available')

	def before_insert(self):
		appointment_event = frappe.new_doc('Event')
		appointment_event = frappe.get_doc({
			'doctype': 'Event',
			'subject': ' '.join(['Appointment with', self.customer_name]),
			'starts_on': self.scheduled_time,
			'status': 'Open',
			'type': 'Private',
			'event_participants': [dict(reference_doctype="Lead", reference_docname=self.lead)]
		})
		appointment_event.insert(ignore_permissions=True)
		self.calendar_event = appointment_event.name

	def after_insert(self):
		available_agents = _get_agents_sorted_by_asc_workload()
		for agent in available_agents:
			if(_check_agent_availability(agent, self.scheduled_time)):
				agent = agent[0]
				agent = frappe.json.loads(agent)[0]
				add_assignemnt({
					'doctype':self.doctype,
					'name':self.name,
					'assign_to':agent
				})
				employee = _get_employee_from_user(agent)
				if employee:
					print(employee)
					calendar_event = frappe.get_doc('Event', self.calendar_event)
					calendar_event.append('event_participants', dict(
						reference_doctype='Employee',
						reference_docname=employee[0].name))
					print(calendar_event)
					calendar_event.save()
				break