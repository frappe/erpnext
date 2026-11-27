# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils import add_days, nowdate

from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
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
	get_on_time_shipments,
	get_rfq_response_days,
	get_rfq_total_number,
	get_sq_total_number,
	get_total_days_late,
	get_total_workdays,
)
from erpnext.stock.doctype.item.test_item import make_item
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

	def test_on_time_and_late_shipments(self):
		supplier = create_scorecard_supplier("_Test Supplier Scorecard On Time")
		on_time_po = create_scorecard_po(supplier, add_days(nowdate(), 5))
		late_po = create_scorecard_po(supplier, add_days(nowdate(), -5), add_days(nowdate(), -10))
		make_purchase_receipt(on_time_po.name).submit()
		self.assertEqual(get_on_time_shipments(scorecard_for(supplier)), 1)

		make_purchase_receipt(late_po.name).submit()
		self.assertEqual(get_on_time_shipments(scorecard_for(supplier)), 1)

	def test_split_on_time_receipts_count_as_one_shipment(self):
		supplier = create_scorecard_supplier("_Test Supplier Scorecard Split")
		po = create_scorecard_po(supplier, add_days(nowdate(), 5))
		for received in (6, 4):
			receipt = make_purchase_receipt(po.name)
			receipt.items[0].qty = received
			receipt.items[0].received_qty = received
			receipt.items[0].stock_qty = received
			receipt.submit()

		self.assertEqual(get_on_time_shipments(scorecard_for(supplier)), 1)

	def test_on_time_receipt_with_rejected_qty_counts_as_on_time(self):
		supplier = create_scorecard_supplier("_Test Supplier Scorecard")
		po = create_scorecard_po(supplier, add_days(nowdate(), 5), qty=10, rate=100)
		receipt = make_purchase_receipt(po.name)
		receipt.items[0].qty = 8
		receipt.items[0].rejected_qty = 2
		receipt.items[0].rejected_warehouse = "_Test Rejected Warehouse - _TC"
		receipt.submit()

		self.assertEqual(get_on_time_shipments(scorecard_for(supplier)), 1)

	def test_on_time_receipt_is_compared_in_stock_qty(self):
		# 2 boxes of 2999.5 received against 2 boxes of 3000 ordered is 1 unit short
		supplier = create_scorecard_supplier("_Test Supplier Scorecard")
		po = create_scorecard_po(supplier, add_days(nowdate(), 5), qty=2, rate=100, submit=False)
		po.items[0].uom = "Box"
		po.items[0].conversion_factor = 3000
		po.submit()
		receipt = make_purchase_receipt(po.name)
		receipt.items[0].conversion_factor = 2999.5
		receipt.submit()

		self.assertEqual(get_on_time_shipments(scorecard_for(supplier)), 0)

	def test_receipts_short_only_by_conversion_rounding_count_as_on_time(self):
		# factors as set from edited stock qtys (332 and 333.42); the PO shows them fully received
		supplier = create_scorecard_supplier("_Test Supplier Scorecard")
		item_code = make_item(properties={"stock_uom": "Kg"}).name
		po = create_scorecard_po(
			supplier, add_days(nowdate(), 5), qty=1467, rate=100, submit=False, item_code=item_code
		)
		po.items[0].uom = "Box"
		po.items[0].conversion_factor = 0.45359237
		po.submit()
		for qty, conversion_factor in ((733, 0.452933151), (734, 0.454250681)):
			receipt = make_purchase_receipt(po.name)
			receipt.items[0].qty = qty
			receipt.items[0].conversion_factor = conversion_factor
			receipt.submit()

		self.assertEqual(get_on_time_shipments(scorecard_for(supplier)), 1)

	def test_short_receipt_rounding_to_ordered_stock_qty_is_late(self):
		supplier = create_scorecard_supplier("_Test Supplier Scorecard")
		po = create_scorecard_po(supplier, add_days(nowdate(), 5), qty=1000, rate=100, submit=False)
		po.items[0].uom = "Box"
		po.items[0].conversion_factor = 0.001
		po.submit()
		receipt = make_purchase_receipt(po.name)
		receipt.items[0].qty = 996
		receipt.submit()

		self.assertEqual(get_on_time_shipments(scorecard_for(supplier)), 0)

	@ERPNextTestSuite.change_settings("Buying Settings", {"allow_zero_qty_in_purchase_order": 1})
	def test_on_time_receipt_against_unit_price_line_counts_as_on_time(self):
		supplier = create_scorecard_supplier("_Test Supplier Scorecard")
		po = create_scorecard_po(supplier, add_days(nowdate(), 5), qty=0, rate=100)
		receipt = make_purchase_receipt(po.name)
		receipt.items[0].qty = 5
		receipt.submit()

		self.assertEqual(get_on_time_shipments(scorecard_for(supplier)), 1)

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


def create_scorecard_po(
	supplier, schedule_date, transaction_date=None, qty=10, rate=100, submit=True, item_code=None
):
	po = create_purchase_order(
		supplier=supplier,
		item_code=item_code,
		transaction_date=transaction_date,
		qty=qty,
		rate=rate,
		do_not_save=True,
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
