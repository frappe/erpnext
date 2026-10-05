# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils import add_days, nowdate

from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import (
	make_all_scorecards,
	refresh_scorecards,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSupplierScorecard(ERPNextTestSuite):
	def test_create_scorecard(self):
		doc = make_supplier_scorecard().insert()
		self.assertEqual(doc.name, valid_scorecard[0].get("supplier"))

	def test_criteria_weight(self):
		my_doc = make_supplier_scorecard()
		for d in my_doc.criteria:
			d.weight = 0
		self.assertRaises(frappe.ValidationError, my_doc.insert)

	def test_make_all_scorecards_refreshes_standing(self):
		doc = make_scorecard_for("_Test Supplier SC Make All")
		doc.criteria[0].criteria_name = make_test_criteria("_Test SC Make All", "100")
		doc.insert()

		frappe.db.delete("Supplier Scorecard Period", {"scorecard": doc.name})
		frappe.db.set_value("Supplier Scorecard Criteria", "_Test SC Make All", "formula", "10")
		self.assertGreater(make_all_scorecards(doc.name), 0)
		self.assertEqual(frappe.db.get_value("Supplier Scorecard", doc.name, "status"), "Very Poor")

	def test_refresh_continues_after_a_failing_scorecard(self):
		scorecards = []
		for supplier_name in ("_Test Supplier SC Refresh Broken", "_Test Supplier SC Refresh Healthy"):
			doc = make_scorecard_for(supplier_name)
			doc.insert()
			scorecards.append(doc.name)
		broken, healthy = scorecards

		frappe.db.delete("Supplier Scorecard Period", {"scorecard": ["in", scorecards]})
		frappe.db.set_value("Supplier Scorecard", broken, "weighting_function", "{total_score} +")
		refresh_scorecards()

		self.assertTrue(frappe.db.exists("Supplier Scorecard Period", {"scorecard": healthy}))
		self.assertTrue(
			frappe.db.exists(
				"Error Log", {"reference_doctype": "Supplier Scorecard", "reference_name": broken}
			)
		)


def make_supplier_scorecard():
	my_doc = frappe.get_doc(valid_scorecard[0])

	# Make sure the criteria exist (making them)
	for d in valid_scorecard[0].get("criteria"):
		if not frappe.db.exists("Supplier Scorecard Criteria", d.get("criteria_name")):
			d["doctype"] = "Supplier Scorecard Criteria"
			d["name"] = d.get("criteria_name")
			my_criteria = frappe.get_doc(d)
			my_criteria.insert()
	return my_doc


valid_scorecard = [
	{
		"standings": [
			{
				"min_grade": 0.0,
				"name": "Very Poor",
				"prevent_rfqs": 1,
				"notify_supplier": 0,
				"doctype": "Supplier Scorecard Scoring Standing",
				"max_grade": 30.0,
				"prevent_pos": 1,
				"warn_pos": 0,
				"warn_rfqs": 0,
				"standing_color": "Red",
				"notify_employee": 0,
				"standing_name": "Very Poor",
				"parenttype": "Supplier Scorecard",
				"parentfield": "standings",
			},
			{
				"min_grade": 30.0,
				"name": "Poor",
				"prevent_rfqs": 1,
				"notify_supplier": 0,
				"doctype": "Supplier Scorecard Scoring Standing",
				"max_grade": 50.0,
				"prevent_pos": 0,
				"warn_pos": 0,
				"warn_rfqs": 0,
				"standing_color": "Red",
				"notify_employee": 0,
				"standing_name": "Poor",
				"parenttype": "Supplier Scorecard",
				"parentfield": "standings",
			},
			{
				"min_grade": 50.0,
				"name": "Average",
				"prevent_rfqs": 0,
				"notify_supplier": 0,
				"doctype": "Supplier Scorecard Scoring Standing",
				"max_grade": 80.0,
				"prevent_pos": 0,
				"warn_pos": 0,
				"warn_rfqs": 0,
				"standing_color": "Green",
				"notify_employee": 0,
				"standing_name": "Average",
				"parenttype": "Supplier Scorecard",
				"parentfield": "standings",
			},
			{
				"min_grade": 80.0,
				"name": "Excellent",
				"prevent_rfqs": 0,
				"notify_supplier": 0,
				"doctype": "Supplier Scorecard Scoring Standing",
				"max_grade": 100.0,
				"prevent_pos": 0,
				"warn_pos": 0,
				"warn_rfqs": 0,
				"standing_color": "Blue",
				"notify_employee": 0,
				"standing_name": "Excellent",
				"parenttype": "Supplier Scorecard",
				"parentfield": "standings",
			},
		],
		"prevent_pos": 0,
		"period": "Per Month",
		"doctype": "Supplier Scorecard",
		"warn_pos": 0,
		"warn_rfqs": 0,
		"notify_supplier": 0,
		"criteria": [
			{
				"weight": 100.0,
				"doctype": "Supplier Scorecard Scoring Criteria",
				"criteria_name": "Delivery",
				"formula": "100",
			}
		],
		"supplier": "_Test Supplier",
		"name": "_Test Supplier",
		"weighting_function": "{total_score} * max( 0, min ( 1 , (12 - {period_number}) / 12) )",
	}
]


def create_test_supplier(supplier_name):
	if not frappe.db.exists("Supplier", supplier_name):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": supplier_name,
				"supplier_group": "_Test Supplier Group",
			}
		).insert()
	return supplier_name


def make_scorecard_for(supplier_name, days_since_creation=75):
	supplier = create_test_supplier(supplier_name)
	frappe.db.set_value("Supplier", supplier, "creation", add_days(nowdate(), -days_since_creation))
	doc = make_supplier_scorecard()
	doc.supplier = doc.name = supplier
	return doc


def make_test_criteria(criteria_name, formula):
	if not frappe.db.exists("Supplier Scorecard Criteria", criteria_name):
		frappe.get_doc(
			{
				"doctype": "Supplier Scorecard Criteria",
				"criteria_name": criteria_name,
				"max_score": 100,
				"weight": 100,
				"formula": formula,
			}
		).insert()
	frappe.db.set_value("Supplier Scorecard Criteria", criteria_name, "formula", formula)
	return criteria_name
