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
		self.assertEquals(test_create_procedure, test_get_procedure.name)
		self.assertEquals(test_create_nested_procedure, test_get_nested_procedure.name)
		self.assertEquals(test_get_nested_procedure.name, test_get_procedure.parent_quality_procedure)

def create_procedure():
	procedure = frappe.get_doc({
		"doctype": "Quality Procedure",
		"procedure": "_Test Quality Procedure",
		"procedure_step": [
			{
				"procedure": "Step",
				"step": "_Test Quality Procedure Table",
			}
		]
	})
	procedure_exist = frappe.db.exists("Quality Procedure",""+ procedure.procedure +"")
	if not procedure_exist:
		procedure.insert()
		return procedure.procedure
	else:
		return procedure_exist

def create_nested_procedure():
	nested_procedure = frappe.get_doc({
		"doctype": "Quality Procedure",
		"procedure": "_Test Nested Quality Procedure",
		"procedure_step": [
			{
				"procedure": "Procedure",
				"procedure_name": "_Test Quality Procedure",
			}
		]
	})
	nested_procedure_exist = frappe.db.exists("Quality Procedure",""+ nested_procedure.procedure +"")
	if not nested_procedure_exist:
		nested_procedure.insert()
		return nested_procedure.procedure
	else:
		return nested_procedure_exist

def get_procedure():
	procedure = frappe.get_all("Quality Procedure", filters={"procedure": "_Test Quality Procedure"}, fields=["name", "parent_quality_procedure"], limit=1)
	nested_procedure = frappe.get_all("Quality Procedure",  filters={"procedure": "_Test Nested Quality Procedure"}, fields=["name", "parent_quality_procedure"], limit=1)
	return procedure[0], nested_procedure[0]
