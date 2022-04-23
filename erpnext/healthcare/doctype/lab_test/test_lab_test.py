# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and Contributors
# See license.txt
from __future__ import unicode_literals
import unittest
import frappe
from frappe.utils import getdate, nowtime
from erpnext.healthcare.doctype.patient_appointment.test_patient_appointment import create_patient
from erpnext.healthcare.doctype.lab_test.lab_test import create_multiple
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_receivable_account, get_income_account
from erpnext.healthcare.doctype.patient_medical_record.test_patient_medical_record import create_lab_test_template as create_blood_test_template

class TestLabTest(unittest.TestCase):
	def test_lab_test_item(self):
		lab_template = create_lab_test_template()
		self.assertTrue(frappe.db.exists('Item', lab_template.item))
		self.assertEqual(frappe.db.get_value('Item Price', {'item_code':lab_template.item}, 'price_list_rate'), lab_template.lab_test_rate)

		lab_template.disabled = 1
		lab_template.save()
		self.assertEqual(frappe.db.get_value('Item', lab_template.item, 'disabled'), 1)

		lab_template.reload()

		lab_template.disabled = 0
		lab_template.save()

	def test_descriptive_lab_test(self):
		lab_template = create_lab_test_template()

		# blank result value not allowed as per template
		lab_test = create_lab_test(lab_template)
		lab_test.descriptive_test_items[0].result_value = 12
		lab_test.descriptive_test_items[2].result_value = 1
		lab_test.save()
		self.assertRaises(frappe.ValidationError, lab_test.submit)

	def test_sample_collection(self):
		frappe.db.set_value('Healthcare Settings', 'Healthcare Settings', 'create_sample_collection_for_lab_test', 1)
		lab_template = create_lab_test_template()

		lab_test = create_lab_test(lab_template)
		lab_test.descriptive_test_items[0].result_value = 12
		lab_test.descriptive_test_items[1].result_value = 1
		lab_test.descriptive_test_items[2].result_value = 2.3
		lab_test.save()

		# check sample collection created
		self.assertTrue(frappe.db.exists('Sample Collection', {'sample': lab_template.sample}))

		frappe.db.set_value('Healthcare Settings', 'Healthcare Settings', 'create_sample_collection_for_lab_test', 0)
		lab_test = create_lab_test(lab_template)
		lab_test.descriptive_test_items[0].result_value = 12
		lab_test.descriptive_test_items[1].result_value = 1
		lab_test.descriptive_test_items[2].result_value = 2.3
		lab_test.save()

		# sample collection should not be created
		lab_test.reload()
		self.assertEqual(lab_test.sample, None)

	def test_create_lab_tests_from_sales_invoice(self):
		sales_invoice = create_sales_invoice()
		create_multiple('Sales Invoice', sales_invoice.name)
		sales_invoice.reload()
		self.assertIsNotNone(sales_invoice.items[0].reference_dn)
		self.assertIsNotNone(sales_invoice.items[1].reference_dn)

	def test_create_lab_tests_from_patient_encounter(self):
		patient_encounter = create_patient_encounter()
		create_multiple('Patient Encounter', patient_encounter.name)
		patient_encounter.reload()
		self.assertTrue(patient_encounter.lab_test_prescription[0].lab_test_created)
		self.assertTrue(patient_encounter.lab_test_prescription[0].lab_test_created)


def create_lab_test_template(test_sensitivity=0, sample_collection=1):
	medical_department = create_medical_department()
	if frappe.db.exists('Lab Test Template', 'Insulin Resistance'):
		return frappe.get_doc('Lab Test Template', 'Insulin Resistance')
	template = frappe.new_doc('Lab Test Template')
	template.lab_test_name = 'Insulin Resistance'
	template.lab_test_template_type = 'Descriptive'
	template.lab_test_code = 'Insulin Resistance'
	template.lab_test_group = 'Services'
	template.department = medical_department
	template.is_billable = 1
	template.lab_test_description = 'Insulin Resistance'
	template.lab_test_rate = 2000

	for entry in ['FBS', 'Insulin', 'IR']:
		template.append('descriptive_test_templates', {
			'particulars': entry,
			'allow_blank': 1 if entry=='IR' else 0
		})

	if test_sensitivity:
		template.sensitivity = 1

	if sample_collection:
		template.sample = create_lab_test_sample()
		template.sample_qty = 5.0

	template.save()
	return template

def create_medical_department():
	medical_department = frappe.db.exists('Medical Department', '_Test Medical Department')
	if not medical_department:
		medical_department = frappe.new_doc('Medical Department')
		medical_department.department = '_Test Medical Department'
		medical_department.save()
		medical_department = medical_department.name

	return medical_department

def create_lab_test(lab_template):
	patient = create_patient()
	lab_test = frappe.new_doc('Lab Test')
	lab_test.template = lab_template.name
	lab_test.patient = patient
	lab_test.patient_sex = 'Female'
	lab_test.save()

	return lab_test

def create_lab_test_sample():
	blood_sample = frappe.db.exists('Lab Test Sample', 'Blood Sample')
	if blood_sample:
		return blood_sample

	sample = frappe.new_doc('Lab Test Sample')
	sample.sample = 'Blood Sample'
	sample.sample_uom = 'U/ml'
	sample.save()

	return sample.name

def create_sales_invoice():
	patient = create_patient()
	medical_department = create_medical_department()
	insulin_resistance_template = create_lab_test_template()
	blood_test_template = create_blood_test_template(medical_department)

	sales_invoice = frappe.new_doc('Sales Invoice')
	sales_invoice.patient = patient
	sales_invoice.customer = frappe.db.get_value('Patient', patient, 'customer')
	sales_invoice.due_date = getdate()
	sales_invoice.company = '_Test Company'
	sales_invoice.debit_to = get_receivable_account('_Test Company')

	tests = [insulin_resistance_template, blood_test_template]
	for entry in tests:
		sales_invoice.append('items', {
			'item_code': entry.item,
			'item_name': entry.lab_test_name,
			'description': entry.lab_test_description,
			'qty': 1,
			'uom': 'Nos',
			'conversion_factor': 1,
			'income_account': get_income_account(None, '_Test Company'),
			'rate': entry.lab_test_rate,
			'amount': entry.lab_test_rate
		})

	sales_invoice.set_missing_values()

	sales_invoice.submit()
	return sales_invoice

def create_patient_encounter():
	patient = create_patient()
	medical_department = create_medical_department()
	insulin_resistance_template = create_lab_test_template()
	blood_test_template = create_blood_test_template(medical_department)

	patient_encounter = frappe.new_doc('Patient Encounter')
	patient_encounter.patient = patient
	patient_encounter.practitioner = create_practitioner()
	patient_encounter.encounter_date = getdate()
	patient_encounter.encounter_time = nowtime()

	tests = [insulin_resistance_template, blood_test_template]
	for entry in tests:
		patient_encounter.append('lab_test_prescription', {
			'lab_test_code': entry.item,
			'lab_test_name': entry.lab_test_name
		})

	patient_encounter.submit()
	return patient_encounter


def create_practitioner():
	practitioner = frappe.db.exists('Healthcare Practitioner', '_Test Healthcare Practitioner')

	if not practitioner:
		practitioner = frappe.new_doc('Healthcare Practitioner')
		practitioner.first_name = '_Test Healthcare Practitioner'
		practitioner.gender = 'Female'
		practitioner.op_consulting_charge = 500
		practitioner.inpatient_visit_charge = 500
		practitioner.save(ignore_permissions=True)
		practitioner = practitioner.name

	return practitioner
