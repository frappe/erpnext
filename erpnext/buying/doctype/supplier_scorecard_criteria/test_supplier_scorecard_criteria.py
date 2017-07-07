# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestSupplierScorecardCriteria(unittest.TestCase):
	def test_variables_exist(self):
		for d in test_good_criteria:
			frappe.get_doc(d).insert()

		self.assertRaises(frappe.ValidationError,frappe.get_doc(test_bad_criteria[0]).insert)

	def test_formula_validate(self):
		self.assertRaises(frappe.ValidationError,frappe.get_doc(test_bad_criteria[1]).insert)
		self.assertRaises(frappe.ValidationError,frappe.get_doc(test_bad_criteria[2]).insert)

test_good_criteria = [
	{
		"name":"Delivery",
		"weight":40.0,
		"doctype":"Supplier Scorecard Criteria",
		"formula":"(({cost_of_on_time_shipments} / {tot_cost_shipments}) if {tot_cost_shipments} > 0 else 1 )* 100",
		"criteria_name":"Delivery",
		"max_score":100.0
	},
]

test_bad_criteria = [
	{
		"name":"Delivery",
		"weight":40.0,
		"doctype":"Supplier Scorecard Criteria",
		"formula":"(({fake_variable} / {tot_cost_shipments}) if {tot_cost_shipments} > 0 else 1 )* 100", # Invalid variable name
		"criteria_name":"Delivery",
		"max_score":100.0
	},
	{
		"name":"Delivery",
		"weight":40.0,
		"doctype":"Supplier Scorecard Criteria",
		"formula":"(({cost_of_on_time_shipments} / {tot_cost_shipments}))* 100", # Force 0 divided by 0
		"criteria_name":"Delivery",
		"max_score":100.0
	},
	{
		"name":"Delivery",
		"weight":40.0,
		"doctype":"Supplier Scorecard Criteria",
		"formula":"(({cost_of_on_time_shipments} {cost_of_on_time_shipments} / {tot_cost_shipments}))* 100", # Two variables beside eachother
		"criteria_name":"Delivery",
		"max_score":100.0
	},
]