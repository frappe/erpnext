# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe.tests import change_settings
from frappe.utils import add_days, today

from erpnext.buying.doctype.request_for_quotation.mapper import make_supplier_quotation_from_rfq
from erpnext.buying.doctype.request_for_quotation.test_request_for_quotation import (
	make_request_for_quotation,
)
from erpnext.buying.doctype.supplier_quotation.mapper import make_purchase_order
from erpnext.buying.doctype.supplier_quotation.supplier_quotation import set_expired_status
from erpnext.controllers.accounts_controller import InvalidQtyError, update_child_qty_rate
from erpnext.tests.utils import ERPNextTestSuite


class TestPurchaseOrder(ERPNextTestSuite):
	def setUp(self):
		self.load_test_records("Supplier Quotation")

	def test_valid_till_before_transaction_date_rejected(self):
		rfq = make_request_for_quotation()
		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=rfq.suppliers[0].supplier)
		sq.transaction_date = today()
		sq.valid_till = add_days(today(), -1)
		self.assertRaises(frappe.ValidationError, sq.insert)

	def test_set_expired_status_expires_only_submitted_past_quotations(self):
		rfq = make_request_for_quotation()

		expired = make_supplier_quotation_from_rfq(rfq.name, for_supplier=rfq.suppliers[0].supplier)
		expired.transaction_date = add_days(today(), -10)
		expired.valid_till = add_days(today(), -2)
		expired.insert()
		expired.submit()

		valid = make_supplier_quotation_from_rfq(rfq.name, for_supplier=rfq.suppliers[1].supplier)
		valid.valid_till = add_days(today(), 10)
		valid.insert()
		valid.submit()

		# A past-validity draft must not be expired - "Expired" applies to submitted quotations only
		draft = make_supplier_quotation_from_rfq(rfq.name, for_supplier=rfq.suppliers[0].supplier)
		draft.transaction_date = add_days(today(), -10)
		draft.valid_till = add_days(today(), -2)
		draft.insert()

		set_expired_status()

		self.assertEqual(frappe.db.get_value("Supplier Quotation", expired.name, "status"), "Expired")
		self.assertEqual(frappe.db.get_value("Supplier Quotation", valid.name, "status"), "Submitted")
		self.assertEqual(frappe.db.get_value("Supplier Quotation", draft.name, "status"), "Draft")

	def test_submit_and_cancel_updates_rfq_quote_status(self):
		rfq = make_request_for_quotation()
		supplier_row = rfq.suppliers[0]

		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=supplier_row.supplier)
		sq.submit()
		self.assertEqual(
			frappe.db.get_value("Request for Quotation Supplier", supplier_row.name, "quote_status"),
			"Received",
		)

		sq.cancel()
		self.assertEqual(
			frappe.db.get_value("Request for Quotation Supplier", supplier_row.name, "quote_status"),
			"Pending",
		)

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
