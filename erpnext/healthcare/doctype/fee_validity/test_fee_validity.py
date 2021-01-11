# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate, add_days
from erpnext.healthcare.doctype.patient_appointment.test_patient_appointment import create_healthcare_docs, create_appointment, create_healthcare_service_items
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile

test_dependencies = ["Company"]

class TestFeeValidity(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabPatient Appointment`""")
		frappe.db.sql("""delete from `tabFee Validity`""")
		frappe.db.sql("""delete from `tabPatient`""")
		make_pos_profile()

	def test_fee_validity(self):
		item = create_healthcare_service_items()
		healthcare_settings = frappe.get_single("Healthcare Settings")
		healthcare_settings.enable_free_follow_ups = 1
		healthcare_settings.max_visits = 2
		healthcare_settings.valid_days = 7
		healthcare_settings.automate_appointment_invoicing = 1
		healthcare_settings.op_consulting_charge_item = item
		healthcare_settings.save(ignore_permissions=True)
		patient, medical_department, practitioner = create_healthcare_docs()

		# appointment should not be invoiced. Check Fee Validity created for new patient
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