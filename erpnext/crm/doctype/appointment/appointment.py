# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Appointment(Document):
	def validate(self):
		number_of_appointments_in_same_slot = frappe.db.count('Appointment',filters={'scheduled_time':self.scheduled_time})
		settings = frappe.get_doc('Appointment Booking Settings')
		if(number_of_appointments_in_same_slot>=settings.number_of_agents):
			frappe.throw('Time slot is not available')

