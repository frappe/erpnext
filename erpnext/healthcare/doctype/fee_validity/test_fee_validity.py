# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.healthcare.doctype.patient_appointment.patient_appointment import create_invoice
from frappe.utils.make_random import get_random
from frappe.utils import nowdate, add_days
# test_records = frappe.get_test_records('Fee Validity')

class TestFeeValidity(unittest.TestCase):
	def test_fee_validity(self):
		patient = get_random("Patient")
		physician = get_random("Physician")

		if not patient:
			patient = frappe.new_doc("Patient")
			patient.patient_name = "Test Patient"
			patient.sex = "Male"
			patient.save(ignore_permissions = True)
			patient = patient.name

		if not physician:
			physician = frappe.new_doc("Physician")
			physician.first_name= "Amit Jain"
			physician.save(ignore_permissions = True)
			physician = physician.name

		frappe.db.set_value("Healthcare Settings", None, "max_visit", 2)
		frappe.db.set_value("Healthcare Settings", None, "valid_days", 7)

		appointment = create_appointment(patient, physician, nowdate())
		invoice = frappe.db.get_value("Patient Appointment", appointment.name, "sales_invoice")
		self.assertEqual(invoice, None)
		create_invoice(frappe.defaults.get_global_default("company"), physician, patient, appointment.name, appointment.appointment_date)
		appointment = create_appointment(patient, physician, add_days(nowdate(), 4))
		invoice = frappe.db.get_value("Patient Appointment", appointment.name, "sales_invoice")
		self.assertTrue(invoice)
		appointment = create_appointment(patient, physician, add_days(nowdate(), 5))
		invoice = frappe.db.get_value("Patient Appointment", appointment.name, "sales_invoice")
		self.assertEqual(invoice, None)
		appointment = create_appointment(patient, physician, add_days(nowdate(), 10))
		invoice = frappe.db.get_value("Patient Appointment", appointment.name, "sales_invoice")
		self.assertEqual(invoice, None)

def create_appointment(patient, physician, appointment_date):
	appointment = frappe.new_doc("Patient Appointment")
	appointment.patient = patient
	appointment.physician = physician
	appointment.appointment_date = appointment_date
	appointment.save(ignore_permissions = True)
	return appointment
