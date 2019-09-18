# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from collections import Counter
from datetime import timedelta

import frappe
from frappe.model.document import Document
from frappe.desk.form.assign_to import add as add_assignemnt


class Appointment(Document):
	def validate(self):
		number_of_appointments_in_same_slot = frappe.db.count('Appointment', filters = {'scheduled_time':self.scheduled_time})
		settings = frappe.get_doc('Appointment Booking Settings')
		if(number_of_appointments_in_same_slot >= settings.number_of_agents):
			frappe.throw('Time slot is not available')

	def before_insert(self):
		self.lead = _find_lead_by_email(self.lead).name
		appointment_event = frappe.get_doc({
			'doctype': 'Event',
			'subject': ' '.join(['Appointment with', self.customer_name]),
			'starts_on': self.scheduled_time,
			'status': 'Open',
			'type': 'Private',
			'event_participants': [dict(reference_doctype = "Lead", reference_docname = self.lead)]
		})
		appointment_event.insert(ignore_permissions=True)
		self.calendar_event = appointment_event.name

	def after_insert(self):
		available_agents = _get_agents_sorted_by_asc_workload()
		for agent in available_agents:
			if(_check_agent_availability(agent, self.scheduled_time)):
				agent = agent[0]
				add_assignemnt({
					'doctype':self.doctype,
					'name':self.name,
					'assign_to':agent
				})
				employee = _get_employee_from_user(agent)
				if employee:
					calendar_event = frappe.get_doc('Event', self.calendar_event)
					calendar_event.append('event_participants', dict(
						reference_doctype= 'Employee',
						reference_docname= employee.name))
					calendar_event.save()
				break

def _get_agents_sorted_by_asc_workload():
	appointments = frappe.db.get_list('Appointment', fields='*')
	agent_list = _get_agent_list_as_strings()	
	if not appointments:
		return agent_list
	appointment_counter = Counter(agent_list)
	for appointment in appointments:
		assigned_to = frappe.parse_json(appointment._assign)
		if not assigned_to:
			continue
		if assigned_to[0] in agent_list:
			appointment_counter[assigned_to[0]] += 1
	sorted_agent_list = appointment_counter.most_common()
	sorted_agent_list.reverse()
	
	return sorted_agent_list

def _find_lead_by_email(email):
    lead_list = frappe.get_list('Lead',filters={'email_id':email},ignore_permissions=True)
    if lead_list:
        return lead_list[0]
    frappe.throw('Email ID not associated with any Lead. Please make sure to use the email address you got this mail on')


def _get_agent_list_as_strings():
	agent_list_as_strings = []
	agent_list = frappe.get_doc('Appointment Booking Settings').agent_list
	for agent in agent_list:
		agent_list_as_strings.append(agent.user)
	return agent_list_as_strings


def _check_agent_availability(agent_email,scheduled_time):
	appointemnts_at_scheduled_time = frappe.get_list('Appointment', filters = {'scheduled_time':scheduled_time})
	for appointment in appointemnts_at_scheduled_time:
		if appointment._assign == agent_email:
			return False
	return True


def _get_employee_from_user(user):
	employee_docname = frappe.db.exists({'doctype':'Employee','user_id':user})
	if employee_docname:
		return frappe.get_doc('Employee',employee_docname[0][0]) # frappe.db.exists returns a tuple of a tuple
	return None
