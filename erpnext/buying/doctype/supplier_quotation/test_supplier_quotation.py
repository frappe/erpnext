# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe.tests import IntegrationTestCase, change_settings
from frappe.utils import add_days, today

from erpnext.buying.doctype.supplier_quotation.supplier_quotation import make_purchase_order
from erpnext.controllers.accounts_controller import InvalidQtyError, update_child_qty_rate


class TestPurchaseOrder(IntegrationTestCase):
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

	def test_update_supplier_quotation_child_rate_disallow(self):
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

	@IntegrationTestCase.change_settings("Buying Settings", {"allow_zero_qty_in_supplier_quotation": 1})
	def test_map_purchase_order_from_zero_qty_supplier_quotation(self):
		sq = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		sq.items[0].qty = 0
		sq.submit()

		po = make_purchase_order(sq.name)
		self.assertEqual(len(po.get("items")), 1)
		self.assertEqual(po.get("items")[0].qty, 0)
		self.assertEqual(po.get("items")[0].item_code, sq.get("items")[0].item_code)
