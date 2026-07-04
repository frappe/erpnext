# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils import add_days, nowdate

from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt as make_pr_from_po
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.supplier_scorecard_variable.supplier_scorecard_variable import (
	VariablePathNotFound,
	get_on_time_shipments,
	get_total_cost_of_shipments,
	get_total_days_late,
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

	def test_total_cost_of_shipments_counts_only_in_period(self):
		supplier = create_scorecard_supplier()
		in_period_po = create_scorecard_po(supplier, nowdate(), qty=10, rate=100)
		create_scorecard_po(supplier, add_days(nowdate(), 60), qty=5, rate=100)  # outside period

		scorecard = scorecard_for(supplier)
		# Compare against base_amount (not a hardcoded total) to stay correct if conversion_rate != 1
		self.assertEqual(get_total_cost_of_shipments(scorecard), in_period_po.items[0].base_amount)

	def test_on_time_and_delayed_shipments(self):
		supplier = create_scorecard_supplier()
		on_time_po = create_scorecard_po(supplier, add_days(nowdate(), 5), qty=10, rate=100)
		late_po = create_scorecard_po(
			supplier,
			add_days(nowdate(), -5),
			transaction_date=add_days(nowdate(), -10),
			qty=10,
			rate=100,
		)
		for po in (on_time_po, late_po):
			receipt = make_pr_from_po(po.name)
			receipt.insert()
			receipt.submit()

		scorecard = scorecard_for(supplier)
		self.assertEqual(get_on_time_shipments(scorecard), 1)
		self.assertEqual(get_total_days_late(scorecard), 50)  # 5 days late * 10 qty

	def test_split_on_time_receipts_count_as_one_shipment(self):
		# A PO line fully received on time across two partial receipts is one on-time shipment
		supplier = create_scorecard_supplier()
		po = create_scorecard_po(supplier, add_days(nowdate(), 5), qty=10, rate=100)
		for received in (6, 4):
			receipt = make_pr_from_po(po.name)
			receipt.items[0].qty = received
			receipt.items[0].received_qty = received
			receipt.items[0].stock_qty = received
			receipt.insert()
			receipt.submit()

		self.assertEqual(get_on_time_shipments(scorecard_for(supplier)), 1)


def create_scorecard_supplier(supplier_name="_Test Supplier Scorecard"):
	if not frappe.db.exists("Supplier", supplier_name):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": supplier_name,
				"supplier_group": "_Test Supplier Group",
			}
		).insert()
	return supplier_name


def create_scorecard_po(supplier, schedule_date, transaction_date=None, qty=10, rate=100):
	po = create_purchase_order(
		supplier=supplier, transaction_date=transaction_date, qty=qty, rate=rate, do_not_save=True
	)
	po.schedule_date = schedule_date
	po.items[0].schedule_date = schedule_date
	po.set_missing_values()
	po.insert()
	po.submit()
	return po


def scorecard_for(supplier):
	return frappe._dict(
		supplier=supplier,
		start_date=add_days(nowdate(), -30),
		end_date=add_days(nowdate(), 30),
	)


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
