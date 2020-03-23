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
	def setUp(self):
		frappe.db.sql("""delete from `tabPatient Appointment`""")
		frappe.db.sql("""delete from `tabFee Validity`""")

	def test_fee_validity(self):
		patient = get_random("Patient")
		practitioner = get_random("Healthcare Practitioner")
		medical_department = get_random("Medical Department")

		item = create_healthcare_service_items()
		healthcare_settings = frappe.get_single("Healthcare Settings")
		healthcare_settings.enable_free_follow_ups = 1
		healthcare_settings.max_visits = 2
		healthcare_settings.valid_days = 7
		healthcare_settings.automate_appointment_invoicing = 1
		healthcare_settings.op_consulting_charge_item = item
		healthcare_settings.save(ignore_permissions=True)

		if not patient:
			patient = frappe.new_doc("Patient")
			patient.first_name = "_Test Patient"
			patient.sex = "Male"
			patient.save(ignore_permissions=True)
			patient = patient.name

		if not medical_department:
			medical_department = frappe.new_doc("Medical Department")
			medical_department.department = "_Test Medical Department"
			medical_department.save(ignore_permissions=True)
			department = medical_department.name

		if not practitioner:
			practitioner = frappe.new_doc("Healthcare Practitioner")
			practitioner.first_name = "_Test Healthcare Practitioner"
			practitioner.gender = 'Female'
			practitioner.department = department
			practitioner.op_consulting_charge = 500
			practitioner.save(ignore_permissions=True)
			practitioner = practitioner.name

		# appointment should not be invoiced as it is within fee validity
		appointment = create_appointment(patient, practitioner, nowdate())
		invoiced = frappe.db.get_value("Patient Appointment", appointment.name, "invoiced")
		self.assertEqual(invoiced, 0)

		# appointment should not be invoiced as it is within fee validity
		appointment = create_appointment(patient, practitioner, add_days(nowdate(), 4))
		invoiced = frappe.db.get_value("Patient Appointment", appointment.name, "invoiced")
		self.assertEqual(invoiced, 0)

		# appointment should be invoiced as it is within fee validity but the max_visits are exceeded
		appointment = create_appointment(patient, practitioner, add_days(nowdate(), 5), invoice=1)
		invoiced = frappe.db.get_value("Patient Appointment", appointment.name, "invoiced")
		self.assertEqual(invoiced, 1)

		# appointment should be invoiced as it is not within fee validity and the max_visits are exceeded
		appointment = create_appointment(patient, practitioner, add_days(nowdate(), 10), invoice=1)
		invoiced = frappe.db.get_value("Patient Appointment", appointment.name, "invoiced")
		self.assertEqual(invoiced, 1)

def create_appointment(patient, practitioner, appointment_date, invoice=0):
	appointment = frappe.new_doc("Patient Appointment")
	appointment.patient = patient
	appointment.practitioner = practitioner
	appointment.department = "_Test Medical Department"
	appointment.appointment_date = appointment_date
	appointment.company = "_Test Company"
	appointment.duration = 15
	if invoice:
		appointment.mode_of_payment = "Cash"
		appointment.paid_amount = 500
	appointment.save(ignore_permissions=True)
	return appointment

def create_healthcare_service_items():
	if frappe.db.exists("Item", "HLC-SI-001"):
		return "HLC-SI-001"
	item = frappe.new_doc("Item")
	item.item_code = "HLC-SI-001"
	item.item_name = "Consulting Charges"
	item.item_group = "Services"
	item.is_stock_item = 0
	item.save()
	return item.name