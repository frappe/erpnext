# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestQualityProcedure(unittest.TestCase):
	def test_quality_procedure(self):
		test_create_procedure = create_procedure()
		test_create_nested_procedure = create_nested_procedure()
		test_get_procedure, test_get_nested_procedure = get_procedure()
		print(test_create_procedure, test_create_nested_procedure)
		print(test_get_procedure, test_get_nested_procedure)
		self.assertEquals(test_create_procedure, test_get_procedure)
		self.assertEquals(test_create_nested_procedure, test_get_nested_procedure)

def create_procedure():
	procedure = frappe.get_doc({
		"doctype": "Quality Procedure",
		"procedure_name": "_Test Quality Procedure",
		"procedures": [
			{
				"process": "_Test Procedure Step 1",
			}
		]
	})
	procedure_exist = frappe.db.get_value("Quality Procedure", {"procedure_name": procedure.procedure_name}, "name")
	if not procedure_exist:
		procedure.insert(ignore_permissions=True)
		return procedure.name
	else:
		return procedure_exist

def create_nested_procedure():
	procedure = create_procedure()
	nested_procedure = frappe.get_doc({
		"doctype": "Quality Procedure",
		"procedure_name": "_Test Nested Quality Procedure",
		"procedures": [
			{
				"link_procedure": procedure,
			}
		]
	})
	nested_procedure_exist = frappe.db.get_value("Quality Procedure", {"procedure_name": nested_procedure.procedure_name}, "name")
	if not nested_procedure_exist:
		nested_procedure.insert(ignore_permissions=True)
		return nested_procedure.name
	else:
		return nested_procedure_exist

def get_procedure():
	return frappe.db.get_value("Quality Procedure", "PRC-_Test Quality Procedure"), \
		frappe.db.get_value("Quality Procedure", "PRC-_Test Nested Quality Procedure")