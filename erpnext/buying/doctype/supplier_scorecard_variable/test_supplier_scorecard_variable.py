# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils import add_days, nowdate

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
	make_supplier_quotation_from_rfq,
)
from erpnext.buying.doctype.request_for_quotation.test_request_for_quotation import (
	make_request_for_quotation,
)
from erpnext.buying.doctype.supplier_scorecard_variable.supplier_scorecard_variable import (
	VariablePathNotFound,
	get_item_workdays,
	get_rfq_response_days,
	get_rfq_total_number,
	get_sq_total_number,
	get_total_days_late,
	get_total_workdays,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSupplierScorecardVariable(ERPNextTestSuite):
	def test_variable_exist(self):
		for d in test_existing_variables:
			my_doc = frappe.get_doc("Supplier Scorecard Variable", d.get("name"))
			self.assertEqual(my_doc.param_name, d.get("param_name"))
			self.assertEqual(my_doc.variable_label, d.get("variable_label"))
			self.assertEqual(my_doc.path, d.get("path"))

	def test_path_exists(self):
		for d in test_good_variables:
			if frappe.db.exists(d):
				frappe.delete_doc(d.get("doctype"), d.get("name"))
			frappe.get_doc(d).insert()

		for d in test_bad_variables:
			self.assertRaises(VariablePathNotFound, frappe.get_doc(d).insert)

	def test_draft_and_cancelled_orders_are_not_late(self):
		supplier = create_scorecard_supplier("_Test Supplier SC Draft Orders")
		ordered_on = add_days(nowdate(), -10)
		create_scorecard_po(supplier, add_days(nowdate(), -5), ordered_on).cancel()
		create_scorecard_po(supplier, add_days(nowdate(), -5), ordered_on, submit=False)

		scorecard = scorecard_for(supplier)
		self.assertEqual(get_total_days_late(scorecard), 0)
		self.assertEqual(get_item_workdays(scorecard), 0)

	def test_rfq_and_quotation_counted_once_per_document(self):
		supplier = create_scorecard_supplier("_Test Supplier SC RFQ Count")
		rfq = make_request_for_quotation(supplier_data=[{"supplier": supplier}], do_not_save=True)
		rfq.transaction_date = add_days(nowdate(), -4)
		for item_code in ("_Test Item 2", "_Test Item Home Desktop 100"):
			rfq.append("items", {**rfq.items[0].as_dict(no_default_fields=True), "item_code": item_code})
		rfq.insert()
		rfq.submit()
		quotation = make_supplier_quotation_from_rfq(rfq.name, for_supplier=supplier)
		quotation.transaction_date = nowdate()
		quotation.insert()
		quotation.submit()

		scorecard = scorecard_for(supplier)
		self.assertEqual(get_rfq_total_number(scorecard), 1)
		self.assertEqual(get_sq_total_number(scorecard), 1)
		self.assertEqual(get_rfq_response_days(scorecard), 4)

	def test_total_workdays_include_both_ends(self):
		scorecard = frappe._dict(start_date="2026-09-01", end_date="2026-09-30")
		self.assertEqual(get_total_workdays(scorecard), 30)


test_existing_variables = [
	{
		"param_name": "total_accepted_items",
		"name": "Total Accepted Items",
		"doctype": "Supplier Scorecard Variable",
		"variable_label": "Total Accepted Items",
		"path": "get_total_accepted_items",
	},
]

test_good_variables = [
	{
		"param_name": "good_variable1",
		"name": "Good Variable 1",
		"doctype": "Supplier Scorecard Variable",
		"variable_label": "Good Variable 1",
		"path": "get_total_accepted_items",
	},
]

test_bad_variables = [
	{
		"param_name": "fake_variable1",
		"name": "Fake Variable 1",
		"doctype": "Supplier Scorecard Variable",
		"variable_label": "Fake Variable 1",
		"path": "get_fake_variable1",
	},
]


def create_scorecard_supplier(supplier_name):
	if not frappe.db.exists("Supplier", supplier_name):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": supplier_name,
				"supplier_group": "_Test Supplier Group",
			}
		).insert()
	return supplier_name


def create_scorecard_po(supplier, schedule_date, transaction_date=None, qty=10, rate=100, submit=True):
	po = create_purchase_order(
		supplier=supplier, transaction_date=transaction_date, qty=qty, rate=rate, do_not_save=True
	)
	po.schedule_date = schedule_date
	po.items[0].schedule_date = schedule_date
	po.set_missing_values()
	po.insert()
	if submit:
		po.submit()
	return po


def scorecard_for(supplier):
	return frappe._dict(
		supplier=supplier,
		start_date=add_days(nowdate(), -30),
		end_date=add_days(nowdate(), 30),
	)
