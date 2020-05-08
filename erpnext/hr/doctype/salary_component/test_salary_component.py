# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

# test_records = frappe.get_test_records('Salary Component')

class TestSalaryComponent(unittest.TestCase):
	pass


def create_salary_component(component_name, **args):
	if not frappe.db.exists("Salary Component", component_name):
			frappe.get_doc({
				"doctype": "Salary Component",
				"salary_component": component_name,
				"type": args.get("type") or "Earning",
				"is_tax_applicable": args.get("is_tax_applicable") or 1
			}).insert()
