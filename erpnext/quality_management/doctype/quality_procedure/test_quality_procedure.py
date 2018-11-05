# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestQualityProcedure(unittest.TestCase):
	def test_quality_procedure(self):
		test_create_procedure = create_procedure()
		test_get_procedure = get_procedure()
		self.assertEquals(test_create_procedure, test_get_procedure)

def create_procedure():
	procedure = frappe.get_doc({
		"doctype": "Quality Procedure",
		"procedure": "_Test Quality Procedure",
		"procedure_step": [
			{
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

def get_procedure():
	procedure = frappe.db.exists("Quality Procedure", "_Test Quality Procedure")
	return procedure