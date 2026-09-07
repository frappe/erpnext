# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, get_last_day, getdate

from erpnext.buying.doctype.supplier.test_supplier import create_supplier


class TestSupplierScorecard(FrappeTestCase):
	def test_create_scorecard(self):
		doc = make_supplier_scorecard().insert()
		self.assertEqual(doc.name, valid_scorecard[0].get("supplier"))

	def test_criteria_weight(self):
		delete_test_scorecards()
		my_doc = make_supplier_scorecard()
		for d in my_doc.criteria:
			d.weight = 0
		self.assertRaises(frappe.ValidationError, my_doc.insert)

	def test_no_recursion_for_supplier_created_on_month_end(self):
		make_supplier_scorecard()  # ensures the "Delivery" criteria master exists

		supplier = create_supplier(supplier_name="_Test Month End Scorecard Supplier")
		month_end = get_last_day(add_months(getdate(), -1))
		frappe.db.set_value("Supplier", supplier.name, "creation", month_end, update_modified=False)

		scorecard = frappe.get_doc(valid_scorecard[0])
		scorecard.supplier = supplier.name
		scorecard.name = supplier.name
		scorecard.insert()

		periods = frappe.get_all(
			"Supplier Scorecard Period",
			filters={"scorecard": scorecard.name},
			fields=["start_date", "end_date"],
		)
		self.assertEqual(len(periods), 1)
		self.assertEqual(periods[0].start_date, month_end)
		self.assertEqual(periods[0].end_date, month_end)

		# saving again must not re-create the single-day period or recurse
		frappe.get_doc("Supplier Scorecard", scorecard.name).save()
		periods = frappe.get_all("Supplier Scorecard Period", filters={"scorecard": scorecard.name})
		self.assertEqual(len(periods), 1)


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


def delete_test_scorecards():
	my_doc = make_supplier_scorecard()
	if frappe.db.exists("Supplier Scorecard", my_doc.name):
		# Delete all the periods, then delete the scorecard
		frappe.db.sql(
			"""delete from `tabSupplier Scorecard Period` where scorecard = %(scorecard)s""",
			{"scorecard": my_doc.name},
		)
		frappe.db.sql(
			"""delete from `tabSupplier Scorecard Scoring Criteria` where parenttype = 'Supplier Scorecard Period'"""
		)
		frappe.db.sql(
			"""delete from `tabSupplier Scorecard Scoring Standing` where parenttype = 'Supplier Scorecard Period'"""
		)
		frappe.db.sql(
			"""delete from `tabSupplier Scorecard Scoring Variable` where parenttype = 'Supplier Scorecard Period'"""
		)
		frappe.delete_doc(my_doc.doctype, my_doc.name)


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
