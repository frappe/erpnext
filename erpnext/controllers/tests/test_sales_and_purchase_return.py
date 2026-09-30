# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestSalesAndPurchaseReturn(ERPNextTestSuite):
	def test_sales_return_validates_against_original(self):
		# Submitting a return Delivery Note runs validate_returned_items (Item / Packed Item lookups
		# via frappe.get_all) and get_already_returned_items (qb GROUP BY of the returned qty) -- both
		# converted from raw SQL here. Exercises them on both engines.
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=100)

		dn = create_delivery_note(qty=5)

		return_dn = make_sales_return(dn.name)
		return_dn.insert()
		return_dn.submit()

		self.assertEqual(return_dn.is_return, 1)
		self.assertEqual(return_dn.items[0].qty, -5)

	def test_purchase_invoice_zero_qty_return_is_rejected(self):
		# A return with every item at qty 0 moves no stock and no value, so it must be
		# rejected the same way a return with no items at all would be.
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice

		pi = make_purchase_invoice(qty=10)

		return_pi = make_purchase_invoice(
			is_return=1,
			return_against=pi.name,
			qty=0,
			do_not_save=True,
		)

		self.assertRaises(frappe.ValidationError, return_pi.save)

	def test_purchase_invoice_item_name_only_zero_qty_return_is_rejected(self):
		# Item Code is not mandatory on Purchase Invoice Item - a row can have only an
		# item_name (e.g. a free-text/non-stock line). Such rows fall through to the
		# item_name-only branch, which must also reject an all-zero-qty return instead
		# of unconditionally treating the row as returned.
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice

		pi = make_purchase_invoice(item_name="_Test Item", qty=10, do_not_submit=True)
		pi.items[0].item_code = ""
		pi.save()
		pi.submit()

		return_pi = make_purchase_invoice(
			item_name="_Test Item",
			is_return=1,
			return_against=pi.name,
			qty=0,
			do_not_save=True,
		)
		return_pi.items[0].item_code = ""

		self.assertRaises(frappe.ValidationError, return_pi.save)

	def test_delivery_note_zero_qty_return_is_rejected(self):
		# A return with every item at qty 0 moves no stock and no value, so it must be
		# rejected the same way a return with no items at all would be.
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=100)

		dn = create_delivery_note(qty=5)

		return_dn = make_sales_return(dn.name)
		return_dn.items[0].qty = 0

		self.assertRaises(frappe.ValidationError, return_dn.insert)

	def test_sales_invoice_zero_qty_return_is_rejected(self):
		# Same rule for a standalone (non stock-affecting) Sales Invoice return: qty 0 on
		# every row must be rejected, not silently accepted as a no-op credit note.
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		si = create_sales_invoice(qty=10)

		return_si = make_return_doc(si.doctype, si.name)
		return_si.items[0].qty = 0

		self.assertRaises(frappe.ValidationError, return_si.save)

	def test_sales_invoice_partial_return_with_different_stock_uom(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.item.test_item import make_item

		item_properties = {"is_stock_item": 1, "stock_uom": "Kg"}
		if frappe.get_meta("Item").has_field("gst_hsn_code") and frappe.db.exists("GST HSN Code", "010121"):
			item_properties["gst_hsn_code"] = "010121"

		item = make_item(
			"_Test SI Return Different Stock UOM",
			item_properties,
			uoms=[{"uom": "Nos", "conversion_factor": 0.013888889}],
		)

		si = create_sales_invoice(item_code=item.name, qty=48, do_not_save=True)
		si.items[0].uom = "Nos"
		si.items[0].stock_uom = "Kg"
		si.items[0].conversion_factor = 0.013888889
		si.save().submit()

		first_return = make_return_doc(si.doctype, si.name)
		first_return.items[0].qty = -24
		first_return.save().submit()

		second_return = make_return_doc(si.doctype, si.name)
		self.assertEqual(second_return.items[0].qty, -24)
		second_return.save().submit()
