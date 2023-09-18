# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase


class TestScorecard(FrappeTestCase):
	def test_create_scorecard(self):
		doc = make_scorecard().insert()
		self.assertEqual(doc.name, valid_scorecard[0].get("party"))

	def test_criteria_weight(self):
		delete_test_scorecards()
		my_doc = make_scorecard()
		for d in my_doc.criteria:
			d.weight = 0
		self.assertRaises(frappe.ValidationError, my_doc.insert)


def make_scorecard():
	my_doc = frappe.get_doc(valid_scorecard[0])

	# Make sure the criteria exist (making them)
	for d in valid_scorecard[0].get("criteria"):
		if not frappe.db.exists("Scorecard Criteria", d.get("criteria_name")):
			d["doctype"] = "Scorecard Criteria"
			d["name"] = d.get("criteria_name")
			my_criteria = frappe.get_doc(d)
			my_criteria.insert()
	return my_doc


def delete_test_scorecards():
	my_doc = make_scorecard()
	if frappe.db.exists("Scorecard", my_doc.name):
		# Delete all the periods, then delete the scorecard
		frappe.db.sql(
			"""delete from `tabScorecard Period` where scorecard = %(scorecard)s""",
			{"scorecard": my_doc.name},
		)
		frappe.db.sql(
			"""delete from `tabScorecard Scoring Criteria` where parenttype = 'Scorecard Period'"""
		)
		frappe.db.sql(
			"""delete from `tabScorecard Scoring Standing` where parenttype = 'Scorecard Period'"""
		)
		frappe.db.sql(
			"""delete from `tabScorecard Scoring Variable` where parenttype = 'Scorecard Period'"""
		)
		frappe.delete_doc(my_doc.doctype, my_doc.name)


valid_scorecard = [
	{
		"standings": [
			{
				"min_grade": 0.0,
				"name": "Very Poor",
				"prevent_rfqs": 1,
				"notify_party": 0,
				"doctype": "Scorecard Scoring Standing",
				"max_grade": 30.0,
				"prevent_pos": 1,
				"warn_pos": 0,
				"warn_rfqs": 0,
				"standing_color": "Red",
				"notify_employee": 0,
				"standing_name": "Very Poor",
				"parenttype": "Scorecard",
				"parentfield": "standings",
			},
			{
				"min_grade": 30.0,
				"name": "Poor",
				"prevent_rfqs": 1,
				"notify_party": 0,
				"doctype": "Scorecard Scoring Standing",
				"max_grade": 50.0,
				"prevent_pos": 0,
				"warn_pos": 0,
				"warn_rfqs": 0,
				"standing_color": "Red",
				"notify_employee": 0,
				"standing_name": "Poor",
				"parenttype": "Scorecard",
				"parentfield": "standings",
			},
			{
				"min_grade": 50.0,
				"name": "Average",
				"prevent_rfqs": 0,
				"notify_party": 0,
				"doctype": "Scorecard Scoring Standing",
				"max_grade": 80.0,
				"prevent_pos": 0,
				"warn_pos": 0,
				"warn_rfqs": 0,
				"standing_color": "Green",
				"notify_employee": 0,
				"standing_name": "Average",
				"parenttype": "Scorecard",
				"parentfield": "standings",
			},
			{
				"min_grade": 80.0,
				"name": "Excellent",
				"prevent_rfqs": 0,
				"notify_party": 0,
				"doctype": "Scorecard Scoring Standing",
				"max_grade": 100.0,
				"prevent_pos": 0,
				"warn_pos": 0,
				"warn_rfqs": 0,
				"standing_color": "Blue",
				"notify_employee": 0,
				"standing_name": "Excellent",
				"parenttype": "Scorecard",
				"parentfield": "standings",
			},
		],
		"prevent_pos": 0,
		"period": "Per Month",
		"doctype": "Scorecard",
		"warn_pos": 0,
		"warn_rfqs": 0,
		"notify_party": 0,
		"criteria": [
			{
				"weight": 100.0,
				"doctype": "Scorecard Scoring Criteria",
				"criteria_name": "Delivery",
				"formula": "100",
			}
		],
		"party_type": "Supplier",
		"party": "_Test Supplier",
		"name": "_Test Supplier",
		"weighting_function": "{total_score} * max( 0, min ( 1 , (12 - {period_number}) / 12) )",
	}
]
