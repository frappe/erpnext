	# -*- coding: utf-8 -*-
# Copyright (c) 2017, ESS LLP and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
import frappe
from erpnext.healthcare.doctype.patient_appointment.test_patient_appointment import create_healthcare_docs, create_clinical_procedure_template

test_dependencies = ['Item']

class TestClinicalProcedure(unittest.TestCase):
	def test_procedure_template_item(self):
		patient, medical_department, practitioner = create_healthcare_docs()
		procedure_template = create_clinical_procedure_template()
		self.assertTrue(frappe.db.exists('Item', procedure_template.item))

		procedure_template.disabled = 1
		procedure_template.save()
		self.assertEqual(frappe.db.get_value('Item', procedure_template.item, 'disabled'), 1)

	def test_consumables(self):
		patient, medical_department, practitioner = create_healthcare_docs()
		procedure_template = create_clinical_procedure_template()
		procedure_template.allow_stock_consumption = 1
		consumable = create_consumable()
		procedure_template.append('items', {
			'item_code': consumable.item_code,
			'qty': 1,
			'uom': consumable.stock_uom,
			'stock_uom': consumable.stock_uom
		})
		procedure_template.save()
		procedure = create_procedure(procedure_template, patient, practitioner)
		result = procedure.start_procedure()
		if result == 'insufficient stock':
			procedure.make_material_receipt(submit=True)
			result = procedure.start_procedure()
		self.assertEqual(procedure.status, 'In Progress')
		result = procedure.complete_procedure()
		# check consumption
		self.assertTrue(frappe.db.exists('Stock Entry', result))


def create_consumable():
	if frappe.db.exists('Item', 'Syringe'):
		return frappe.get_doc('Item', 'Syringe')
	consumable = frappe.new_doc('Item')
	consumable.item_code = 'Syringe'
	consumable.item_group = '_Test Item Group'
	consumable.stock_uom = 'Nos'
	consumable.valuation_rate = 5.00
	consumable.save()
	return consumable

def create_procedure(procedure_template, patient, practitioner):
	procedure = frappe.new_doc('Clinical Procedure')
	procedure.procedure_template = procedure_template.name
	procedure.patient = patient
	procedure.practitioner = practitioner
	procedure.consume_stock = procedure_template.allow_stock_consumption
	procedure.items = procedure_template.items
	procedure.company = "_Test Company"
	procedure.warehouse = "_Test Warehouse - _TC"
	procedure.submit()
	return procedure