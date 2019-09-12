# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from datetime import timedelta
import frappe
from frappe.model.document import Document

class Appointment(Document):
	def validate(self):
		number_of_appointments_in_same_slot = frappe.db.count('Appointment',filters={'scheduled_time':self.scheduled_time})
		settings = frappe.get_doc('Appointment Booking Settings')
		if(number_of_appointments_in_same_slot>=settings.number_of_agents):
			frappe.throw('Time slot is not available')
	
	def before_insert(self):
		appointment_event = frappe.new_doc('Event')
		appointment_event.subject = 'Appointment with ' + self.customer_name
		appointment_event.starts_on = self.scheduled_time
		appointment_event.status = 'Open'
		appointment_event.type = 'Private'
		settings = frappe.get_doc('Appointment Booking Settings')
		appointment_event.ends_on = self.scheduled_time + timedelta(minutes=settings.appointment_duration)
		event_participants = []
		event_participant_customer = frappe.new_doc('Event Participants')
		event_participant_customer.reference_doctype = 'Lead'
		event_participant_customer.reference_docname = self.lead
		event_participants.append(event_participant_customer)
		appointment_event.event_participants = event_participants
		appointment_event.insert()
		self.calender_event = appointment_event.name

