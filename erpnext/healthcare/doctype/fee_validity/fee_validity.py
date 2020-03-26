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
		self.set_start_date()

	def update_status(self):
		if self.visited >= self.max_visits:
			self.status = 'Completed'
		else:
			self.status = 'Pending'

	def set_start_date(self):
		self.start_date = getdate()
		for appointment in self.ref_appointments:
			appointment_date = frappe.db.get_value('Patient Appointment', appointment.appointment, 'appointment_date')
			if getdate(appointment_date) < self.start_date:
				self.start_date = getdate(appointment_date)


def create_fee_validity(appointment):
	if not check_is_new_patient(appointment):
		return

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

def check_is_new_patient(appointment):
	validity_exists = frappe.db.exists('Fee Validity', {
		'practitioner': appointment.practitioner,
		'patient': appointment.patient
	})
	if validity_exists:
		return False

	appointment_exists = frappe.db.get_all('Patient Appointment', {
		'name': ('!=', appointment.name),
		'status': ('!=', 'Cancelled'),
		'patient': appointment.patient,
		'practitioner': appointment.practitioner
	})
	if len(appointment_exists) and appointment_exists[0]:
		return False
	return True