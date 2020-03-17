# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe.utils import getdate
import datetime

class FeeValidity(Document):
	def validate(self):
		self.update_status()

	def update_status(self):
		valid_till = getdate(self.valid_till)
		today  = getdate()
		if self.visited >= self.max_visits:
			self.status = 'Completed'
		elif self.visited < self.max_visits:
			if valid_till >= today:
				self.status = 'Ongoing'
			elif valid_till < today:
				self.status = 'Expired'

def create_fee_validity(appointment):
	fee_validity = frappe.new_doc('Fee Validity')
	fee_validity.practitioner = appointment.practitioner
	fee_validity.patient = appointment.patient
	fee_validity.max_visits = frappe.db.get_single_value('Healthcare Settings', 'max_visits') or 1
	valid_days = frappe.db.get_single_value('Healthcare Settings', 'valid_days') or 1
	fee_validity.visited = 1
	fee_validity.valid_till = getdate(appointment.appointment_date) + datetime.timedelta(days=int(valid_days))
	fee_validity.append('ref_appointments', {
		'appointment': appointment.name
	})
	fee_validity.save(ignore_permissions=True)
	return fee_validity

def update_validity_status():
	docs = frappe.get_all('Fee Validity', filters={'status': ['not in', ['Completed', 'Expired']]})
	for doc in docs:
		frappe.get_doc("Task", doc.name).update_status()
