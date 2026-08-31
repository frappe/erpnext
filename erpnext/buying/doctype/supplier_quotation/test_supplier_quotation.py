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
from erpnext.patches.v16_0.set_supplier_quotation_order_status import execute as set_order_status
from erpnext.tests.assertions import assert_raises_with_savepoint
from erpnext.tests.utils import ERPNextTestSuite


class TestPurchaseOrder(ERPNextTestSuite):
	def setUp(self):
		self.load_test_records("Supplier Quotation")

	def make_order(self, supplier_quotation, qty):
		purchase_order = make_purchase_order(supplier_quotation.name)
		purchase_order.naming_series = "_T-Purchase Order-"
		purchase_order.items[0].qty = qty
		purchase_order.items[0].schedule_date = add_days(today(), 1)
		purchase_order.insert()
		purchase_order.submit()
		return purchase_order

	def update_order_qty(self, purchase_order, qty):
		item = purchase_order.items[0]
		items = json.dumps(
			[{"item_code": item.item_code, "rate": item.rate, "qty": qty, "docname": item.name}]
		)
		update_child_qty_rate("Purchase Order", items, purchase_order.name)
		purchase_order.reload()

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

		partially_ordered = make_supplier_quotation_from_rfq(rfq.name, for_supplier=rfq.suppliers[1].supplier)
		partially_ordered.valid_till = add_days(today(), 10)
		partially_ordered.items[0].qty = 10
		partially_ordered.insert()
		partially_ordered.submit()
		partial_order = self.make_order(partially_ordered, 4)
		partially_ordered.db_set("valid_till", add_days(today(), -2))

		# A past-validity draft must not be expired - "Expired" applies to submitted quotations only
		draft = make_supplier_quotation_from_rfq(rfq.name, for_supplier=rfq.suppliers[0].supplier)
		draft.transaction_date = add_days(today(), -10)
		draft.valid_till = add_days(today(), -2)
		draft.insert()

		set_expired_status()

		self.assertEqual(frappe.db.get_value("Supplier Quotation", expired.name, "status"), "Expired")
		self.assertEqual(frappe.db.get_value("Supplier Quotation", valid.name, "status"), "Submitted")
		self.assertEqual(
			frappe.db.get_value("Supplier Quotation", partially_ordered.name, "status"),
			"Partially Ordered",
		)
		self.assertEqual(frappe.db.get_value("Supplier Quotation", draft.name, "status"), "Draft")

		partial_order.cancel()
		self.assertEqual(
			frappe.db.get_value("Supplier Quotation", partially_ordered.name, "status"),
			"Submitted",
		)

		set_expired_status()
		self.assertEqual(
			frappe.db.get_value("Supplier Quotation", partially_ordered.name, "status"),
			"Expired",
		)

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

	def test_purchase_order_updates_order_status(self):
		supplier_quotation = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		supplier_quotation.submit()

		partial_order = self.make_order(supplier_quotation, 4)
		supplier_quotation.reload()
		self.assertEqual(supplier_quotation.status, "Partially Ordered")
		self.assertEqual(supplier_quotation.items[0].ordered_qty, 4)

		self.update_order_qty(partial_order, 10)
		supplier_quotation.reload()
		self.assertEqual(supplier_quotation.status, "Ordered")
		self.assertEqual(supplier_quotation.items[0].ordered_qty, 10)

		self.update_order_qty(partial_order, 4)
		supplier_quotation.reload()
		self.assertEqual(supplier_quotation.status, "Partially Ordered")

		complete_order = self.make_order(supplier_quotation, 6)
		supplier_quotation.reload()
		self.assertEqual(supplier_quotation.status, "Ordered")

		complete_order.cancel()
		supplier_quotation.reload()
		self.assertEqual(supplier_quotation.status, "Partially Ordered")

		partial_order.cancel()
		supplier_quotation.reload()
		self.assertEqual(supplier_quotation.status, "Submitted")
		self.assertEqual(supplier_quotation.items[0].ordered_qty, 0)

	def test_purchase_order_maps_remaining_quotation_qty(self):
		supplier_quotation = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		supplier_quotation.submit()
		self.make_order(supplier_quotation, 4)

		purchase_order = make_purchase_order(supplier_quotation.name)
		self.assertEqual(purchase_order.items[0].qty, 6)

		purchase_order.items[0].schedule_date = add_days(today(), 1)
		purchase_order.submit()

		supplier_quotation.reload()
		self.assertEqual(supplier_quotation.status, "Ordered")
		self.assertEqual(make_purchase_order(supplier_quotation.name).items, [])

	def test_purchase_order_skips_fully_ordered_quotation_rows(self):
		supplier_quotation = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		supplier_quotation.append("items", {"item_code": "_Test Item 2", "qty": 3, "rate": 100})
		supplier_quotation.submit()

		first_order = make_purchase_order(
			supplier_quotation.name,
			args={"filtered_children": [supplier_quotation.items[0].name]},
		)
		first_order.items[0].schedule_date = add_days(today(), 1)
		first_order.submit()

		supplier_quotation.reload()
		self.assertEqual(supplier_quotation.status, "Partially Ordered")

		second_order = make_purchase_order(supplier_quotation.name)
		self.assertEqual(len(second_order.items), 1)
		self.assertEqual(second_order.items[0].item_code, "_Test Item 2")
		self.assertEqual(second_order.items[0].qty, 3)

		second_order.items[0].schedule_date = add_days(today(), 1)
		second_order.submit()
		supplier_quotation.reload()
		self.assertEqual(supplier_quotation.status, "Ordered")

	def test_purchase_order_cannot_exceed_supplier_quotation_qty(self):
		supplier_quotation = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		supplier_quotation.items[0].qty = 5
		supplier_quotation.submit()

		first_order = make_purchase_order(supplier_quotation.name)
		second_order = make_purchase_order(supplier_quotation.name)
		for purchase_order in (first_order, second_order):
			purchase_order.items[0].schedule_date = add_days(today(), 1)

		first_order.submit()
		self.assertRaises(frappe.ValidationError, second_order.submit)

	def test_removing_purchase_order_item_updates_quotation_status(self):
		first_quotation = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		first_quotation.submit()
		second_quotation = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		second_item = second_quotation.items[0]
		second_item.item_code = second_item.item_name = "_Test Item 2"
		second_item.stock_uom = second_item.uom = frappe.db.get_value("Item", "_Test Item 2", "stock_uom")
		second_item.conversion_factor = 1
		second_quotation.submit()

		purchase_order = make_purchase_order(first_quotation.name)
		purchase_order = make_purchase_order(second_quotation.name, purchase_order)
		purchase_order.naming_series = "_T-Purchase Order-"
		for item in purchase_order.items:
			item.schedule_date = add_days(today(), 1)
		purchase_order.insert()
		purchase_order.submit()

		first_quotation.reload()
		second_quotation.reload()
		self.assertEqual(first_quotation.status, "Ordered")
		self.assertEqual(second_quotation.status, "Ordered")

		remaining_item = next(
			item for item in purchase_order.items if item.supplier_quotation == second_quotation.name
		)
		update_child_qty_rate(
			"Purchase Order",
			json.dumps(
				[
					{
						"item_code": remaining_item.item_code,
						"rate": remaining_item.rate,
						"qty": remaining_item.qty,
						"docname": remaining_item.name,
					}
				]
			),
			purchase_order.name,
		)

		first_quotation.reload()
		second_quotation.reload()
		self.assertEqual(first_quotation.status, "Submitted")
		self.assertEqual(second_quotation.status, "Ordered")

	def test_order_status_patch_updates_existing_quotation(self):
		supplier_quotation = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		supplier_quotation.submit()
		self.make_order(supplier_quotation, 4)

		supplier_quotation.db_set("status", "Submitted")
		frappe.db.set_value("Supplier Quotation Item", supplier_quotation.items[0].name, "ordered_qty", 0)
		set_order_status()

		supplier_quotation.reload()
		self.assertEqual(supplier_quotation.status, "Partially Ordered")
		self.assertEqual(supplier_quotation.items[0].ordered_qty, 4)

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

	def test_update_child_qty_with_conversion_factor_after_purchase(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(uoms=[{"uom": "Box", "conversion_factor": 5}])
		supplier_quotation = frappe.copy_doc(self.globalTestRecords["Supplier Quotation"][0])
		supplier_quotation.items[0].item_code = item.item_code
		supplier_quotation.items[0].qty = 6
		supplier_quotation.items[0].uom = "Box"
		supplier_quotation.items[0].conversion_factor = 5
		supplier_quotation.insert()
		supplier_quotation.submit()

		purchase_order = make_purchase_order(supplier_quotation.name)
		purchase_order.schedule_date = add_days(today(), 1)
		purchase_order.items[0].qty = 2
		purchase_order.save()
		purchase_order.submit()

		def update_qty(qty):
			row = supplier_quotation.items[0]
			trans_items = json.dumps(
				[
					{
						"item_code": row.item_code,
						"rate": row.rate,
						"qty": qty,
						"uom": row.uom,
						"conversion_factor": 2,
						"docname": row.name,
					}
				]
			)
			update_child_qty_rate("Supplier Quotation", trans_items, supplier_quotation.name)

		update_qty(5)
		supplier_quotation.reload()
		self.assertEqual(supplier_quotation.items[0].conversion_factor, 2)
		self.assertEqual(supplier_quotation.items[0].stock_qty, 10)

		self.assertRaisesRegex(
			frappe.ValidationError,
			"Cannot reduce quantity than ordered or purchased quantity",
			update_qty,
			4,
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

		# check if item having purchase order can be removed
		with assert_raises_with_savepoint(self, frappe.LinkExistsError):
			update_child_qty_rate("Supplier Quotation", trans_item, sq.name)

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
