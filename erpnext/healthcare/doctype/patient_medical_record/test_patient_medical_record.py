# Copyright (c) 2015, ESS LLP and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.healthcare.doctype.patient_appointment.test_patient_appointment import (
	create_appointment,
	create_encounter,
	create_healthcare_docs,
	create_medical_department,
)


class TestPatientMedicalRecord(unittest.TestCase):
	def setUp(self):
		frappe.db.set_value("Healthcare Settings", None, "enable_free_follow_ups", 0)
		frappe.db.set_value("Healthcare Settings", None, "automate_appointment_invoicing", 1)
		frappe.db.sql("delete from `tabPatient Appointment`")
		make_pos_profile()

	def test_medical_record(self):
		patient, practitioner = create_healthcare_docs()
		medical_department = create_medical_department()
		appointment = create_appointment(patient, practitioner, nowdate(), invoice=1)
		encounter = create_encounter(appointment)

		# check for encounter
		medical_rec = frappe.db.exists(
			"Patient Medical Record", {"status": "Open", "reference_name": encounter.name}
		)
		self.assertTrue(medical_rec)

		vital_signs = create_vital_signs(appointment)
		# check for vital signs
		medical_rec = frappe.db.exists(
			"Patient Medical Record", {"status": "Open", "reference_name": vital_signs.name}
		)
		self.assertTrue(medical_rec)

		appointment = create_appointment(
			patient, practitioner, add_days(nowdate(), 1), invoice=1, procedure_template=1
		)
		procedure = create_procedure(appointment)
		procedure.start_procedure()
		procedure.complete_procedure()
		# check for clinical procedure
		medical_rec = frappe.db.exists(
			"Patient Medical Record", {"status": "Open", "reference_name": procedure.name}
		)
		self.assertTrue(medical_rec)

		template = create_lab_test_template(medical_department)
		lab_test = create_lab_test(template.name, patient)
		# check for lab test
		medical_rec = frappe.db.exists(
			"Patient Medical Record", {"status": "Open", "reference_name": lab_test.name}
		)
		self.assertTrue(medical_rec)


def create_procedure(appointment):
	if appointment:
		procedure = frappe.new_doc("Clinical Procedure")
		procedure.procedure_template = appointment.procedure_template
		procedure.appointment = appointment.name
		procedure.patient = appointment.patient
		procedure.practitioner = appointment.practitioner
		procedure.medical_department = appointment.department
		procedure.start_dt = appointment.appointment_date
		procedure.start_time = appointment.appointment_time
		procedure.save()
		procedure.submit()
		return procedure


def create_vital_signs(appointment):
	vital_signs = frappe.new_doc("Vital Signs")
	vital_signs.patient = appointment.patient
	vital_signs.signs_date = appointment.appointment_date
	vital_signs.signs_time = appointment.appointment_time
	vital_signs.temperature = 38.5
	vital_signs.save()
	vital_signs.submit()
	return vital_signs


def create_lab_test_template(medical_department):
	if frappe.db.exists("Lab Test Template", "Blood Test"):
		return frappe.get_doc("Lab Test Template", "Blood Test")

	template = frappe.new_doc("Lab Test Template")
	template.lab_test_name = "Blood Test"
	template.lab_test_code = "Blood Test"
	template.lab_test_group = "Services"
	template.department = medical_department
	template.is_billable = 1
	template.lab_test_rate = 2000
	template.save()
	return template


def create_lab_test(template, patient):
	lab_test = frappe.new_doc("Lab Test")
	lab_test.patient = patient
	lab_test.patient_sex = frappe.db.get_value("Patient", patient, "sex")
	lab_test.template = template
	lab_test.save()
	lab_test.submit()
	return lab_test
