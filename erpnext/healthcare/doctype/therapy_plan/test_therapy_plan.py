# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import getdate
from erpnext.healthcare.doctype.therapy_type.test_therapy_type import create_therapy_type
from erpnext.healthcare.doctype.therapy_plan.therapy_plan import make_therapy_session

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

def create_healthcare_docs():
	patient = create_patient()
	practitioner = frappe.db.exists('Healthcare Practitioner', '_Test Healthcare Practitioner')
	medical_department = frappe.db.exists('Medical Department', '_Test Medical Department')

	if not medical_department:
		medical_department = frappe.new_doc('Medical Department')
		medical_department.department = '_Test Medical Department'
		medical_department.save(ignore_permissions=True)
		medical_department = medical_department.name

	if not practitioner:
		practitioner = frappe.new_doc('Healthcare Practitioner')
		practitioner.first_name = '_Test Healthcare Practitioner'
		practitioner.gender = 'Female'
		practitioner.department = medical_department
		practitioner.op_consulting_charge = 500
		practitioner.inpatient_visit_charge = 500
		practitioner.save(ignore_permissions=True)
		practitioner = practitioner.name

	return patient, medical_department, practitioner

def create_patient():
	patient = frappe.db.exists('Patient', '_Test Patient')
	if not patient:
		patient = frappe.new_doc('Patient')
		patient.patient_name = '_Test Patient'
		patient.sex = 'Female'
		patient.save(ignore_permissions=True)
		patient = patient.name
	return patient