# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils.make_random import get_random
from frappe.utils import nowdate, add_days, getdate

test_dependencies = ["Company"]

class TestFeeValidity(unittest.TestCase):
	def test_fee_validity(self):
		frappe.db.sql("""delete from `tabPatient Appointment`""")
		frappe.db.sql("""delete from `tabFee Validity`""")
		patient = get_random("Patient")
		practitioner = get_random("Healthcare Practitioner")
		department = get_random("Medical Department")

		if not patient:
			patient = frappe.new_doc("Patient")
			patient.patient_name = "_Test Patient"
			patient.sex = "Male"
			patient.save(ignore_permissions=True)
			patient = patient.name

		if not department:
			medical_department = frappe.new_doc("Medical Department")
			medical_department.department = "_Test Medical Department"
			medical_department.save(ignore_permissions=True)
			department = medical_department.name

		if not practitioner:
			practitioner = frappe.new_doc("Healthcare Practitioner")
			practitioner.first_name = "_Test Healthcare Practitioner"
			practitioner.department = department
			practitioner.save(ignore_permissions=True)
			practitioner = practitioner.name



		frappe.db.set_value("Healthcare Settings", None, "max_visit", 2)
		frappe.db.set_value("Healthcare Settings", None, "valid_days", 7)

		appointment = create_appointment(patient, practitioner, nowdate(), department)
		invoiced = frappe.db.get_value("Patient Appointment", appointment.name, "invoiced")
		self.assertEqual(invoiced, 0)

		invoice_appointment(appointment)

		appointment = create_appointment(patient, practitioner, add_days(nowdate(), 4), department)
		invoiced = frappe.db.get_value("Patient Appointment", appointment.name, "invoiced")
		self.assertTrue(invoiced)

		appointment = create_appointment(patient, practitioner, add_days(nowdate(), 5), department)
		invoiced = frappe.db.get_value("Patient Appointment", appointment.name, "invoiced")
		self.assertEqual(invoiced, 0)

		appointment = create_appointment(patient, practitioner, add_days(nowdate(), 10), department)
		invoiced = frappe.db.get_value("Patient Appointment", appointment.name, "invoiced")
		self.assertEqual(invoiced, 0)

def create_appointment(patient, practitioner, appointment_date, department):
	appointment = frappe.new_doc("Patient Appointment")
	appointment.patient = patient
	appointment.practitioner = practitioner
	appointment.department = department
	appointment.appointment_date = appointment_date
	appointment.company = "_Test Company"
	appointment.save(ignore_permissions=True)
	return appointment

def invoice_appointment(appointment_doc):
	if not appointment_doc.name:
		return False
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", appointment_doc.patient, "customer")
	sales_invoice.due_date = getdate()
	sales_invoice.is_pos = 0
	sales_invoice.company = appointment_doc.company
	sales_invoice.debit_to = "_Test Receivable - _TC"

	create_invoice_items(appointment_doc, sales_invoice)

	sales_invoice.save(ignore_permissions=True)
	sales_invoice.submit()

def create_invoice_items(appointment, invoice):
	item_line = invoice.append("items")
	item_line.item_name = "Consulting Charges"
	item_line.description = "Consulting Charges:  " + appointment.practitioner
	item_line.uom = "Nos"
	item_line.conversion_factor = 1
	item_line.income_account = "_Test Account Cost for Goods Sold - _TC"
	item_line.cost_center = "_Test Cost Center - _TC"
	item_line.rate = 250
	item_line.amount = 250
	item_line.qty = 1
	item_line.reference_dt = "Patient Appointment"
	item_line.reference_dn = appointment.name

	return invoice
