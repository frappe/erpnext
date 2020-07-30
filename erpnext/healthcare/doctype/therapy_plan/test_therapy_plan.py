# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import getdate
from erpnext.healthcare.doctype.therapy_type.test_therapy_type import create_therapy_type
from erpnext.healthcare.doctype.therapy_plan.therapy_plan import make_therapy_session
from erpnext.healthcare.doctype.patient_appointment.test_patient_appointment import create_healthcare_docs, create_patient

class TestTherapyPlan(unittest.TestCase):
	def test_creation_on_encounter_submission(self):
		patient, medical_department, practitioner = create_healthcare_docs()
		encounter = create_encounter(patient, medical_department, practitioner)
		self.assertTrue(frappe.db.exists('Therapy Plan', encounter.therapy_plan))

	def test_status(self):
		plan = create_therapy_plan()
		self.assertEquals(plan.status, 'Not Started')

		session = make_therapy_session(plan.name, plan.patient, 'Basic Rehab')
		frappe.get_doc(session).submit()
		self.assertEquals(frappe.db.get_value('Therapy Plan', plan.name, 'status'), 'In Progress')

		session = make_therapy_session(plan.name, plan.patient, 'Basic Rehab')
		frappe.get_doc(session).submit()
		self.assertEquals(frappe.db.get_value('Therapy Plan', plan.name, 'status'), 'Completed')


def create_therapy_plan():
	patient = create_patient()
	therapy_type = create_therapy_type()
	plan = frappe.new_doc('Therapy Plan')
	plan.patient = patient
	plan.start_date = getdate()
	plan.append('therapy_plan_details', {
		'therapy_type': therapy_type.name,
		'no_of_sessions': 2
	})
	plan.save()
	return plan

def create_encounter(patient, medical_department, practitioner):
	encounter = frappe.new_doc('Patient Encounter')
	encounter.patient = patient
	encounter.practitioner = practitioner
	encounter.medical_department = medical_department
	therapy_type = create_therapy_type()
	encounter.append('therapies', {
		'therapy_type': therapy_type.name,
		'no_of_sessions': 2
	})
	encounter.save()
	encounter.submit()
	return encounter
