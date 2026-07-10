# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import (
	get_scorecard_date,
	make_all_scorecards,
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

	def test_overlapping_standings_are_rejected(self):
		doc = make_supplier_scorecard()
		# "Poor" (30-50) stretched to 60 now overlaps "Average" (50-80)
		doc.standings[1].max_grade = 60
		self.assertRaises(frappe.ValidationError, doc.validate_standings)

	def test_standings_must_cover_full_range(self):
		doc = make_supplier_scorecard()
		# "Excellent" capped at 90 leaves the 90-100 band uncovered
		doc.standings[3].max_grade = 90
		self.assertRaises(frappe.ValidationError, doc.validate_standings)

	def test_inverted_standing_band_rejected(self):
		doc = make_supplier_scorecard()
		doc.standings = []
		doc.append("standings", {"standing_name": "Inverted", "min_grade": 60, "max_grade": 40})
		self.assertRaises(frappe.ValidationError, doc.validate_standings)

	def test_perfect_score_maps_to_top_standing(self):
		# A perfect score (the upper bound of the top band) must still resolve to a standing
		supplier = create_test_supplier("_Test Supplier SC Perfect")
		doc = make_supplier_scorecard()
		doc.supplier = supplier
		doc.supplier_score = 100
		doc.update_standing()
		self.assertEqual(doc.status, "Excellent")

	def test_total_score_defaults_to_100_without_periods(self):
		doc = make_supplier_scorecard()
		doc.name = "_Test Scorecard Without Periods"
		doc.calculate_total_score()
		self.assertEqual(doc.supplier_score, 100)

	def test_update_standing_propagates_blocking_flags_to_supplier(self):
		supplier = create_test_supplier("_Test Supplier SC Standing")
		doc = make_supplier_scorecard()
		doc.supplier = supplier
		doc.supplier_score = 20  # falls in the "Very Poor" (0-30) band
		doc.update_standing()

		self.assertEqual(doc.status, "Very Poor")
		self.assertEqual(doc.prevent_pos, 1)
		self.assertEqual(doc.prevent_rfqs, 1)
		self.assertEqual(frappe.db.get_value("Supplier", supplier, "prevent_pos"), 1)
		self.assertEqual(frappe.db.get_value("Supplier", supplier, "prevent_rfqs"), 1)

	def test_scorecard_period_end_dates(self):
		start = getdate("2024-01-01")
		self.assertEqual(get_scorecard_date("Per Week", start), getdate("2024-01-08"))
		self.assertEqual(get_scorecard_date("Per Month", start), getdate("2024-01-31"))
		self.assertEqual(get_scorecard_date("Per Year", start), getdate("2024-12-31"))

	def test_make_all_scorecards_is_idempotent(self):
		supplier = create_test_supplier("_Test Supplier SC Idempotent")
		frappe.db.set_value("Supplier", supplier, "creation", add_days(nowdate(), -75))

		frappe.delete_doc_if_exists("Supplier Scorecard", supplier)
		doc = make_supplier_scorecard()
		doc.supplier = supplier
		doc.name = supplier
		doc.insert()  # on_update generates the period scorecards

		created = frappe.db.count("Supplier Scorecard Period", {"scorecard": doc.name, "docstatus": 1})
		self.assertGreater(created, 0)
		self.assertEqual(make_all_scorecards(doc.name), 0)


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
