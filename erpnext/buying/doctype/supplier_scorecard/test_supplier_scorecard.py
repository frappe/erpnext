# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from itertools import pairwise
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import (
	get_scorecard_date,
	make_all_scorecards,
	refresh_scorecards,
)
from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import (
	make_supplier_scorecard as make_scorecard_period,
)
from erpnext.setup.doctype.employee.test_employee import make_employee


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

	@patch("erpnext.buying.doctype.supplier_scorecard.supplier_scorecard.nowdate", lambda: "2026-09-15")
	def test_no_recursion_for_supplier_created_on_month_end(self):
		make_supplier_scorecard()  # ensures the "Delivery" criteria master exists

		supplier = create_supplier(supplier_name="_Test Month End Scorecard Supplier")
		month_end = getdate("2026-08-31")
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

	def test_deleting_scorecard_keeps_flags_of_another_scorecard(self):
		doc = make_very_poor_scorecard("_Test Supplier SC Delete Old")
		renamed = frappe.rename_doc("Supplier", doc.supplier, "_Test Supplier SC Delete New")
		make_very_poor_scorecard(renamed)

		frappe.db.delete("Supplier Scorecard Period", {"scorecard": doc.name})
		frappe.delete_doc("Supplier Scorecard", doc.name)

		self.assertEqual(frappe.db.get_value("Supplier", renamed, "prevent_pos"), 1)

	def test_deleting_scorecard_clears_supplier_flags(self):
		doc = make_very_poor_scorecard("_Test Supplier SC Delete")
		self.assertEqual(frappe.db.get_value("Supplier", doc.supplier, "prevent_pos"), 1)

		frappe.db.delete("Supplier Scorecard Period", {"scorecard": doc.name})
		doc.delete()

		flags = frappe.db.get_value(
			"Supplier", doc.supplier, ["prevent_pos", "prevent_rfqs", "warn_pos", "warn_rfqs"]
		)
		self.assertFalse(any(flags))

	def test_renamed_supplier_keeps_scorecard_block(self):
		doc = make_very_poor_scorecard("_Test Supplier SC Rename")
		renamed = frappe.rename_doc("Supplier", doc.supplier, "_Test Supplier SC Renamed")

		po = create_purchase_order(supplier=renamed, do_not_save=True)
		self.assertRaises(frappe.ValidationError, po.validate_supplier)

	def test_scorecard_period_end_dates(self):
		start = getdate("2024-01-01")
		self.assertEqual(get_scorecard_date("Per Week", start), getdate("2024-01-07"))
		self.assertEqual(get_scorecard_date("Per Month", start), getdate("2024-01-31"))
		self.assertEqual(get_scorecard_date("Per Year", start), getdate("2024-12-31"))

	def test_weekly_periods_continue_after_an_existing_period(self):
		doc = make_scorecard_for("_Test Supplier SC Legacy Week", days_since_creation=0)
		doc.period = "Per Week"
		doc.insert()
		start = getdate(add_days(nowdate(), -30))
		legacy_period = make_scorecard_period(doc.name, None)
		legacy_period.start_date = start
		legacy_period.end_date = add_days(start, 7)
		legacy_period.insert()
		legacy_period.submit()
		frappe.db.set_value("Supplier", doc.supplier, "creation", start)

		make_all_scorecards(doc.name)

		periods = frappe.get_all(
			"Supplier Scorecard Period",
			filters={"scorecard": doc.name, "docstatus": 1},
			fields=["start_date", "end_date"],
			order_by="start_date",
		)
		for previous, current in pairwise(periods):
			self.assertEqual(current.start_date, add_days(previous.end_date, 1))

	def test_period_ending_today_is_not_created(self):
		doc = make_scorecard_for("_Test Supplier SC Ends Today", days_since_creation=6)
		doc.period = "Per Week"
		doc.insert()

		self.assertFalse(frappe.db.exists("Supplier Scorecard Period", {"scorecard": doc.name}))

	def test_criteria_weights_allow_float_rounding(self):
		doc = make_supplier_scorecard()
		doc.criteria = []
		for weight in (10.1, 66.6, 23.3):
			doc.append("criteria", {"criteria_name": "Delivery", "weight": weight})
		doc.validate_criteria_weights()

	def test_standing_change_notifies_supplier_and_employee(self):
		frappe.get_doc(
			{
				"doctype": "Email Account",
				"enable_outgoing": 1,
				"default_outgoing": 1,
				"awaiting_password": 1,
				"auth_method": "Basic",
				"password": "test",
				"smtp_server": "localhost",
				"email_id": "scorecard.outgoing@example.com",
			}
		).insert()
		employee = make_employee("scorecard.employee@example.com", company="_Test Company")
		doc = make_scorecard_for("_Test Supplier SC Notify")
		frappe.db.set_value("Supplier", doc.supplier, "email_id", "scorecard.supplier@example.com")
		doc.criteria[0].criteria_name = make_test_criteria("_Test SC Very Poor", "10")
		doc.standings[0].update({"notify_supplier": 1, "notify_employee": 1, "employee_link": employee})
		doc.insert()
		doc.save()

		self.assertEqual(doc.employee, employee)
		queues = frappe.get_all("Email Queue", {"reference_name": doc.name}, pluck="name")
		recipients = frappe.get_all("Email Queue Recipient", {"parent": ["in", queues]}, pluck="recipient")
		self.assertCountEqual(
			recipients, ["scorecard.employee@example.com", "scorecard.supplier@example.com"]
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


def make_very_poor_scorecard(supplier_name):
	doc = make_scorecard_for(supplier_name)
	doc.criteria[0].criteria_name = make_test_criteria("_Test SC Very Poor", "10")
	doc.insert()
	return doc
