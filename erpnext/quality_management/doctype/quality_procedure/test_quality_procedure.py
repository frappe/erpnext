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

		self.assertEquals(test_create_procedure, test_get_procedure.get("name"))
		self.assertEquals(test_create_nested_procedure, test_get_nested_procedure.get("name"))

def create_procedure():
	procedure = frappe.get_doc({
		"doctype": "Quality Procedure",
		"quality_procedure_name": "_Test Quality Procedure",
		"processes": [
			{
				"process_description": "_Test Quality Procedure Table",
			}
		]
	})

	procedure_exist = frappe.db.exists("Quality Procedure", "PRC-_Test Quality Procedure")

	if not procedure_exist:
		procedure.insert()
		return procedure.name
	else:
		return procedure_exist

def create_nested_procedure():
	nested_procedure = frappe.get_doc({
		"doctype": "Quality Procedure",
		"quality_procedure_name": "_Test Nested Quality Procedure",
		"processes": [
			{
				"procedure": "PRC-_Test Quality Procedure"
			}
		]
	})

	nested_procedure_exist = frappe.db.exists("Quality Procedure", "PRC-_Test Nested Quality Procedure")

	if not nested_procedure_exist:
		nested_procedure.insert()
		return nested_procedure.name
	else:
		return nested_procedure_exist

def get_procedure():
	procedure = frappe.get_doc("Quality Procedure", "PRC-_Test Quality Procedure")
	nested_procedure = frappe.get_doc("Quality Procedure",  "PRC-_Test Nested Quality Procedure")
	return {"name": procedure.name}, {"name": nested_procedure.name, "parent_quality_procedure": nested_procedure.parent_quality_procedure}