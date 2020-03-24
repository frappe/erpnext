# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils.make_random import get_random
from frappe.utils import nowdate, add_days, getdate
from erpnext.healthcare.doctype.patient_appointment.test_patient_appointment import create_healthcare_docs, create_appointment

test_dependencies = ["Company"]

class TestFeeValidity(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabPatient Appointment`""")
		frappe.db.sql("""delete from `tabFee Validity`""")

	def test_fee_validity(self):
		patient, medical_department, practitioner = create_healthcare_docs()
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