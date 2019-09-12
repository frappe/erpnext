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
		appointment_event = frappe.get_doc({
			"doctype": "Event",
			"subject": ' '.join(['Appointment with', self.customer_name]),
			"starts_on": self.scheduled_time,
			"status": "Open",
			"type": "Private",
			"event_participants": [dict(reference_doctype="Lead", reference_docname=self.lead)]
		})
	
		appointment_event.insert(ignore_permissions=True)
		self.calender_event = appointment_event.name

