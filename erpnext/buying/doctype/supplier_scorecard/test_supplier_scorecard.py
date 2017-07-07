# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestSupplierScorecard(unittest.TestCase):

	def test_create_scorecard(self):
		my_doc = make_supplier_scorecard()
		delete_test_scorecards()
		my_doc.insert()

	def test_criteria_weight(self):
		my_doc = make_supplier_scorecard()
		delete_test_scorecards()
		for d in my_doc.criteria:
			d.weight = 0
		self.assertRaises(frappe.ValidationError,my_doc.insert)

	def test_missing_variable(self):
		my_doc = make_supplier_scorecard()
		delete_test_scorecards()
		del my_doc.variables
		self.assertRaises(frappe.ValidationError,my_doc.insert)

def make_supplier_scorecard():
	return frappe.get_doc(valid_scorecard[0])

def delete_test_scorecards():
	my_doc = make_supplier_scorecard()
	if frappe.db.exists("Supplier Scorecard", my_doc.name):
		# Delete all the periods, then delete the scorecard
		frappe.db.sql("""delete from `tabSupplier Scorecard Period` where scorecard = %(scorecard)s""", {'scorecard': my_doc.name})
		frappe.delete_doc(my_doc.doctype, my_doc.name)

valid_scorecard = [
	{
		"standings":[
			{
				"min_grade":0.0,"name":"Very Poor",
				"prevent_rfqs":1,
				"notify_supplier":0,
				"doctype":"Supplier Scorecard Standing",
				"max_grade":30.0,
				"prevent_pos":1,
				"warn_pos":0,
				"warn_rfqs":0,
				"standing_color":"Red",
				"notify_employee":0,
				"standing_name":"Very Poor",
				"parenttype":"Supplier Scorecard",
				"parentfield":"standings"
			},
			{
				"min_grade":30.0,
				"name":"Poor",
				"prevent_rfqs":1,
				"notify_supplier":0,
				"doctype":"Supplier Scorecard Standing",
				"max_grade":50.0,
				"prevent_pos":0,
				"warn_pos":0,
				"warn_rfqs":0,
				"standing_color":"Red",
				"notify_employee":0,
				"standing_name":"Poor",
				"parenttype":"Supplier Scorecard",
				"parentfield":"standings"
			},
			{
				"min_grade":50.0,
				"name":"Average",
				"prevent_rfqs":0,
				"notify_supplier":0,
				"doctype":"Supplier Scorecard Standing",
				"max_grade":80.0,
				"prevent_pos":0,
				"warn_pos":0,
				"warn_rfqs":0,
				"standing_color":"Green",
				"notify_employee":0,
				"standing_name":"Average",
				"parenttype":"Supplier Scorecard",
				"parentfield":"standings"
			},
			{
				"min_grade":80.0,
				"name":"Excellent",
				"prevent_rfqs":0,
				"notify_supplier":0,
				"doctype":"Supplier Scorecard Standing",
				"max_grade":100.0,
				"prevent_pos":0,
				"warn_pos":0,
				"warn_rfqs":0,
				"standing_color":"Blue",
				"notify_employee":0,
				"standing_name":"Excellent",
				"parenttype":"Supplier Scorecard",
				"parentfield":"standings"
			}
		],
		"prevent_pos":0,
		"variables": [
			{
				"param_name":"cost_of_on_time_shipments",
				"parent":"Paramount Components",
				"doctype":"Supplier Scorecard Scoring Variable",
				"parenttype":"Supplier Scorecard",
				"variable_label":"Cost of On Time Shipments",
				"path":"get_cost_of_on_time_shipments",
				"parentfield":"variables"
			},
			{
				"param_name":"tot_cost_shipments",
				"parent":"Paramount Components",
				"doctype":"Supplier Scorecard Scoring Variable",
				"parenttype":"Supplier Scorecard",
				"variable_label":"Total Cost of Shipments",
				"path":"get_total_cost_of_shipments",
				"parentfield":"variables"
			},
			{
				"param_name":"tot_days_late",
				"parent":"Paramount Components",
				"doctype":"Supplier Scorecard Scoring Variable",
				"parenttype":"Supplier Scorecard",
				"variable_label":"Total Days Late",
				"path":"get_total_days_late",
				"parentfield":"variables"
			},
			{
				"param_name":"total_working_days",
				"parent":"Paramount Components",
				"doctype":"Supplier Scorecard Scoring Variable",
				"parenttype":"Supplier Scorecard",
				"variable_label":"Total Working Days",
				"path":"get_total_workdays",
				"parentfield":"variables"
			},
			{
				"param_name":"on_time_shipment_num",
				"parent":"Paramount Components",
				"doctype":"Supplier Scorecard Scoring Variable",
				"parenttype":"Supplier Scorecard",
				"variable_label":"# of On Time Shipments",
				"path":"get_on_time_shipments",
				"parentfield":"variables"
			},
			{
				"param_name":"total_shipments",
				"parent":"Paramount Components",
				"doctype":"Supplier Scorecard Scoring Variable",
				"parenttype":"Supplier Scorecard",
				"variable_label":"Total Shipments",
				"path":"get_total_shipments",
				"parentfield":"variables"
			}
		],
		"period":"Per Month",
		"doctype":"Supplier Scorecard",
		"warn_pos":0,
		"warn_rfqs":0,
		"notify_supplier":0,
		"criteria":[
			{
				"parent":"Paramount Components",
				"weight":100.0,
				"doctype":"Supplier Scorecard Scoring Criteria",
				"parenttype":"Supplier Scorecard",
				"formula":"(({cost_of_on_time_shipments} / {tot_cost_shipments}) if {tot_cost_shipments} > 0 else 1 )* 100 ",
				"criteria_name":"Delivery",
				"max_score":100.0,
				"parentfield":"criteria"
			}
		],
		"supplier":"_Test Supplier",
		"name":"_Test Supplier",
		"weighting_function":"{total_score} * max( 0, min ( 1 , (12 - {period_number}) / 12) )",
	}
]

