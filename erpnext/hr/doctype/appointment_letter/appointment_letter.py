# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class AppointmentLetter(Document):
	pass

@frappe.whitelist()
def get_appointment_letter_details(template):
	body = []
	intro= frappe.get_list("Appointment Letter Template",
		fields = ['introduction', 'closing_notes'],
		filters={'name': template
	})[0]
	content = frappe.get_list("Appointment Letter content",
		fields = ['title', 'description'],
		filters={'parent': template
	})
	body.append(intro)
	body.append({'description': content})
	return body
