# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe.tests import change_settings
from frappe.utils import add_days, today

from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
	make_supplier_quotation_from_rfq,
)
from erpnext.buying.doctype.request_for_quotation.test_request_for_quotation import (
	make_request_for_quotation,
)
from erpnext.buying.doctype.supplier_quotation.supplier_quotation import make_purchase_order
from erpnext.controllers.accounts_controller import InvalidQtyError, update_child_qty_rate
from erpnext.tests.utils import ERPNextTestSuite


class TestPurchaseOrder(ERPNextTestSuite):
	def setUp(self):
		self.load_test_records("Supplier Quotation")

	def test_update_child_supplier_quotation_add_item(self):
		sq = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		sq.submit()

		trans_item = json.dumps(
			[
				{
					"item_code": sq.items[0].item_code,
					"rate": sq.items[0].rate,
					"qty": 5,
					"docname": sq.items[0].name,
				},
				{"item_code": "_Test Item 2", "rate": 300, "qty": 3, "description": "test"},
			]
		)
		update_child_qty_rate("Supplier Quotation", trans_item, sq.name)
		sq.reload()
		self.assertEqual(sq.get("items")[0].qty, 5)
		self.assertEqual(sq.get("items")[1].rate, 300)
		self.assertEqual(sq.get("items")[1].description, "test")

	def test_update_supplier_quotation_child_rate(self):
		sq = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		sq.submit()
		trans_item = json.dumps(
			[
				{
					"item_code": sq.items[0].item_code,
					"rate": 300,
					"qty": sq.items[0].qty,
					"docname": sq.items[0].name,
				},
			]
		)
		update_child_qty_rate("Supplier Quotation", trans_item, sq.name)
		sq.reload()
		self.assertEqual(sq.get("items")[0].rate, 300)
		po = make_purchase_order(sq.name)
		po.schedule_date = add_days(today(), 1)
		po.submit()
		trans_item = json.dumps(
			[
				{
					"item_code": sq.items[0].item_code,
					"rate": 20,
					"qty": sq.items[0].qty,
					"docname": sq.items[0].name,
				},
			]
		)
		self.assertRaises(
			frappe.ValidationError, update_child_qty_rate, "Supplier Quotation", trans_item, sq.name
		)

	def test_update_supplier_quotation_child_remove_item(self):
		sq = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		sq.submit()
		po = make_purchase_order(sq.name)

		trans_item = json.dumps(
			[
				{
					"item_code": sq.items[0].item_code,
					"rate": sq.items[0].rate,
					"qty": sq.items[0].qty,
					"docname": sq.items[0].name,
				},
				{
					"item_code": "_Test Item 2",
					"rate": 300,
					"qty": 3,
				},
			]
		)
		po.get("items")[0].schedule_date = add_days(today(), 1)
		update_child_qty_rate("Supplier Quotation", trans_item, sq.name)
		po.submit()
		sq.reload()

		trans_item = json.dumps(
			[
				{
					"item_code": "_Test Item 2",
					"rate": 300,
					"qty": 3,
				}
			]
		)

		frappe.db.savepoint("before_cancel")
		# check if item having purchase order can be removed
		self.assertRaises(
			frappe.LinkExistsError, update_child_qty_rate, "Supplier Quotation", trans_item, sq.name
		)
		frappe.db.rollback(save_point="before_cancel")

		trans_item = json.dumps(
			[
				{
					"item_code": sq.items[0].item_code,
					"rate": sq.items[0].rate,
					"qty": sq.items[0].qty,
					"docname": sq.items[0].name,
				}
			]
		)

		update_child_qty_rate("Supplier Quotation", trans_item, sq.name)
		sq.reload()
		self.assertEqual(len(sq.get("items")), 1)

	def test_supplier_quotation_qty(self):
		sq = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		sq.items[0].qty = 0
		with self.assertRaises(InvalidQtyError):
			sq.save()

		# No error with qty=1
		sq.items[0].qty = 1
		sq.save()
		self.assertEqual(sq.items[0].qty, 1)

	def test_supplier_quotation_zero_qty_cannot_be_forced_by_the_client(self):
		sq = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		sq.items[0].qty = 0
		sq.has_unit_price_items = 1

		with self.assertRaises(InvalidQtyError):
			sq.save()

	def test_supplier_quotation_zero_qty(self):
		"""
		Test if RFQ with zero qty (Unit Price Item) is conditionally allowed.
		"""
		sq = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		sq.items[0].qty = 0

		with change_settings("Buying Settings", {"allow_zero_qty_in_supplier_quotation": 1}):
			sq.save()
			self.assertEqual(sq.items[0].qty, 0)

	def test_make_purchase_order(self):
		sq = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0]).insert()

		self.assertRaises(frappe.ValidationError, make_purchase_order, sq.name)

		sq = frappe.get_doc("Supplier Quotation", sq.name)
		sq.submit()
		po = make_purchase_order(sq.name)

		self.assertEqual(po.doctype, "Purchase Order")
		self.assertEqual(len(po.get("items")), len(sq.get("items")))

		po.naming_series = "_T-Purchase Order-"

		for doc in po.get("items"):
			if doc.get("item_code"):
				doc.set("schedule_date", add_days(today(), 1))

		po.insert()

	@ERPNextTestSuite.change_settings("Buying Settings", {"allow_zero_qty_in_supplier_quotation": 1})
	def test_map_purchase_order_from_zero_qty_supplier_quotation(self):
		sq = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		sq.items[0].qty = 0
		sq.submit()

		po = make_purchase_order(sq.name)
		self.assertEqual(len(po.get("items")), 1)
		self.assertEqual(po.get("items")[0].qty, 0)
		self.assertEqual(po.get("items")[0].item_code, sq.get("items")[0].item_code)

	def test_removing_quoted_rows_resets_rfq_quote_status(self):
		rfq = make_request_for_quotation(do_not_submit=True)
		rfq.append("items", dict(rfq.items[0].as_dict(), name=None, idx=None, item_code="_Test Item 2"))
		rfq.submit()
		supplier = rfq.suppliers[0].supplier
		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=supplier)
		sq.submit()
		self.assertEqual(rfq_quote_status(rfq.name, supplier), "Received")

		row = sq.items[0]
		trans_items = json.dumps(
			[{"item_code": row.item_code, "rate": row.rate, "qty": row.qty, "docname": row.name}]
		)
		update_child_qty_rate("Supplier Quotation", trans_items, sq.name)

		self.assertEqual(rfq_quote_status(rfq.name, supplier), "Pending")

	def test_removing_only_rfq_row_resets_rfq_quote_status(self):
		rfq = make_request_for_quotation()
		supplier = rfq.suppliers[0].supplier
		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=supplier)
		sq.append("items", {"item_code": "_Test Item 2", "qty": 1, "rate": 100})
		sq.submit()
		self.assertEqual(rfq_quote_status(rfq.name, supplier), "Received")

		row = sq.items[1]
		trans_items = json.dumps(
			[{"item_code": row.item_code, "rate": row.rate, "qty": row.qty, "docname": row.name}]
		)
		update_child_qty_rate("Supplier Quotation", trans_items, sq.name)

		self.assertEqual(rfq_quote_status(rfq.name, supplier), "Pending")


def rfq_quote_status(rfq, supplier):
	return frappe.db.get_value(
		"Request for Quotation Supplier", {"parent": rfq, "supplier": supplier}, "quote_status"
	)
