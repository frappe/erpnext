# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt

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

	def test_return_qty_is_checked_when_only_qty_changes(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=100)
		dn = create_delivery_note(qty=5)

		return_dn = make_sales_return(dn.name)
		return_dn.items[0].qty = -50

		self.assertRaises(frappe.ValidationError, return_dn.insert)

	def test_delivery_note_return_row_without_reference_is_limited_to_delivered_qty(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=100)
		dn = create_delivery_note(qty=5)

		return_dn = make_sales_return(dn.name)
		return_dn.items[0].dn_detail = None
		return_dn.items[0].qty = return_dn.items[0].stock_qty = -50
		self.assertRaises(frappe.ValidationError, return_dn.insert)

		return_dn.items[0].qty = return_dn.items[0].stock_qty = -5
		return_dn.items[0].item_code = "_Test Item 2"
		self.assertRaises(frappe.ValidationError, return_dn.insert)

		return_dn.items[0].item_code = "_Test Item"
		return_dn.insert()
		return_dn.submit()

	def test_delivery_note_returns_with_and_without_dn_detail_share_the_delivered_qty(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=100)
		dn = create_delivery_note(qty=5)

		unlinked_return = make_sales_return(dn.name)
		unlinked_return.items[0].dn_detail = None
		unlinked_return.items[0].qty = unlinked_return.items[0].stock_qty = -4
		unlinked_return.insert()
		unlinked_return.submit()

		linked_return = make_sales_return(dn.name)
		linked_return.items[0].qty = linked_return.items[0].stock_qty = -4
		self.assertRaises(frappe.ValidationError, linked_return.insert)

		two_row_return = make_sales_return(create_delivery_note(qty=5).name)
		two_row_return.append("items", dict(two_row_return.items[0].as_dict(), name=None, dn_detail=None))
		self.assertRaises(frappe.ValidationError, two_row_return.insert)

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_to_edit_stock_uom_qty_for_sales": 0})
	def test_delivery_note_return_rows_add_up_unrounded_stock_qty(self):
		return_dn = make_split_return_of_box_item(conversion_factor=0.3356, delivery_rows=1)
		return_dn.insert()

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_to_edit_stock_uom_qty_for_sales": 1})
	def test_delivery_note_return_rows_add_up_rounded_stock_qty_when_editable(self):
		return_dn = make_split_return_of_box_item(conversion_factor=0.3334, delivery_rows=3)
		return_dn.insert()

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_to_edit_stock_uom_qty_for_sales": 1})
	def test_delivery_note_split_return_of_one_row_when_stock_qty_is_editable(self):
		return_dn = make_split_return_of_box_item(conversion_factor=0.3356, delivery_rows=1)
		return_dn.insert()

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_to_edit_stock_uom_qty_for_sales": 1})
	def test_delivery_note_split_return_of_one_row_submits_as_fully_returned(self):
		return_dn = make_split_return_of_box_item(conversion_factor=0.3356, delivery_rows=1)
		for row in return_dn.items:
			row.dn_detail = return_dn.items[0].dn_detail
		return_dn.submit()

		self.assertEqual(frappe.db.get_value("Delivery Note", return_dn.return_against, "per_returned"), 100)

	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_to_edit_stock_uom_qty_for_sales": 1})
	def test_delivery_note_return_of_rounded_stock_qty_in_stock_uom(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return

		# stock qty rounds up, then down
		for conversion_factor in (0.3356, 0.3344):
			with self.subTest(conversion_factor=conversion_factor):
				dn = make_box_delivery_note(conversion_factor)
				return_dn = make_sales_return(dn.name)
				row = return_dn.items[0]
				row.uom, row.conversion_factor, row.qty = "Kg", 1, -dn.items[0].stock_qty
				return_dn.submit()

				self.assertEqual(frappe.db.get_value("Delivery Note", dn.name, "per_returned"), 100)

	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_to_edit_stock_uom_qty_for_sales": 1})
	def test_delivery_note_returns_of_invoiced_row_get_full_credit(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice, make_sales_return

		dn = make_box_delivery_note(conversion_factor=0.3356)
		make_sales_invoice(dn.name).submit()

		for _ in range(3):
			return_dn = make_sales_return(dn.name)
			return_dn.items[0].qty = -1
			return_dn.issue_credit_note = 1
			return_dn.submit()
			credited_qty = frappe.db.get_value(
				"Sales Invoice Item", {"dn_detail": return_dn.items[0].name, "docstatus": 1}, "qty"
			)
			self.assertEqual(credited_qty, -1)

	def test_purchase_receipt_split_return_of_one_row_submits_as_fully_returned(self):
		from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_return
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		conversion_factor = 0.3356
		item_code = make_box_item(conversion_factor)
		# spare stock, so this test checks only the return status
		make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=1, basic_rate=100)
		pr = make_purchase_receipt(item_code=item_code, qty=3, uom="Box", conversion_factor=conversion_factor)

		return_pr = make_purchase_return(pr.name)
		return_pr.items[0].qty = return_pr.items[0].received_qty = -1
		for _ in range(2):
			return_pr.append("items", dict(return_pr.items[0].as_dict(), name=None))
		return_pr.submit()

		self.assertEqual(frappe.db.get_value("Purchase Receipt", pr.name, "per_returned"), 100)

	def test_purchase_receipt_split_return_takes_out_the_received_stock_qty(self):
		from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_return
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		conversion_factor = 0.3356
		pr = make_purchase_receipt(
			item_code=make_box_item(conversion_factor),
			qty=3,
			uom="Box",
			stock_uom="Kg",
			conversion_factor=conversion_factor,
		)

		return_pr = make_purchase_return(pr.name)
		return_pr.items[0].qty = return_pr.items[0].received_qty = -1
		for _ in range(2):
			return_pr.append("items", dict(return_pr.items[0].as_dict(), name=None))
		return_pr.submit()

		self.assertEqual(get_posted_stock_qty(return_pr), -get_posted_stock_qty(pr))

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_to_edit_stock_uom_qty_for_sales": 1})
	def test_delivery_note_split_return_brings_back_the_delivered_stock_qty(self):
		return_dn = make_split_return_of_box_item(conversion_factor=0.3356, delivery_rows=1)
		return_dn.submit()

		dn = frappe.get_doc("Delivery Note", return_dn.return_against)
		self.assertEqual(get_posted_stock_qty(return_dn), -get_posted_stock_qty(dn))

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	def test_delivery_note_full_return_when_earlier_rows_round_up(self):
		return_dn = make_split_return_of_box_item(conversion_factor=0.338, delivery_rows=3)
		return_dn.insert()

	@ERPNextTestSuite.change_settings("Stock Settings", {"allow_to_edit_stock_uom_qty_for_sales": 1})
	def test_delivery_note_bundle_return_counts_components_on_rounded_stock_qty(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		conversion_factor = 0.301
		_component, bundle = make_bundle_with_component(
			component_qty=10,
			bundle_properties={
				"stock_uom": "Kg",
				"uoms": [
					{"uom": "Kg", "conversion_factor": 1},
					{"uom": "Box", "conversion_factor": conversion_factor},
				],
			},
		)
		dn = create_delivery_note(item_code=bundle, qty=1, do_not_submit=True)
		dn.items[0].uom, dn.items[0].conversion_factor = "Box", conversion_factor
		dn.submit()

		make_sales_return(dn.name).insert()

	def test_delivery_note_return_of_component_counts_its_packed_qty(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		component, bundle = make_bundle_with_component(component_qty=10)
		dn = create_delivery_note(item_code=component, qty=1, do_not_submit=True)
		dn.append("items", dict(dn.items[0].as_dict(), name=None, item_code=bundle))
		dn.submit()

		create_delivery_note(is_return=1, return_against=dn.name, item_code=component, qty=-5)

		component_return = create_delivery_note(
			is_return=1, return_against=dn.name, item_code=component, qty=-7, do_not_save=True
		)
		self.assertRaises(frappe.ValidationError, component_return.insert)

	def test_delivery_note_return_of_component_delivered_only_in_bundle_is_capped(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		component, bundle = make_bundle_with_component(component_qty=10)
		dn = create_delivery_note(item_code=bundle, qty=1)

		component_return = create_delivery_note(
			is_return=1, return_against=dn.name, item_code=component, qty=-50, do_not_save=True
		)
		self.assertRaises(frappe.ValidationError, component_return.insert)

		make_sales_return(dn.name).submit()
		component_return.items[0].qty = -1
		self.assertRaises(frappe.ValidationError, component_return.insert)

	def test_delivery_note_bundle_return_counts_earlier_component_returns(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		component, bundle = make_bundle_with_component(component_qty=10)
		dn = create_delivery_note(item_code=bundle, qty=1)
		create_delivery_note(is_return=1, return_against=dn.name, item_code=component, qty=-5)

		self.assertRaises(frappe.ValidationError, make_sales_return(dn.name).insert)

	def test_bundle_return_keeps_order_qty_after_component_uom_change(self):
		from erpnext.selling.doctype.sales_order.mapper import make_delivery_note
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		warehouse = "_Test Warehouse - _TC"
		component = make_item(
			properties={"stock_uom": "Nos", "uoms": [{"uom": "Box", "conversion_factor": 10}]}
		)
		make_stock_entry(item=component.name, to_warehouse=warehouse, qty=100, rate=100)
		bundle = make_item(properties={"is_stock_item": 0}).name
		bundle_doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": bundle})
		bundle_doc.append("items", {"item_code": component.name, "qty": 1, "uom": "Box"})
		bundle_doc.insert()
		bundle_doc.submit()

		sales_order = make_sales_order(item_code=bundle, warehouse=warehouse, qty=2)  # 20 Nos
		next(row for row in component.uoms if row.uom == "Box").conversion_factor = 12
		component.save()

		delivery_note = make_delivery_note(sales_order.name)
		delivery_note.submit()

		return_note = make_sales_return(delivery_note.name)
		return_note.submit()
		self.assertEqual(return_note.packed_items[0].qty, -20)

	def test_bundle_return_keeps_delivered_qty_after_component_uom_change(self):
		from erpnext.stock.doctype.delivery_note.mapper import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		warehouse = "_Test Warehouse - _TC"
		component = make_item(
			properties={"stock_uom": "Nos", "uoms": [{"uom": "Box", "conversion_factor": 10}]}
		)
		make_stock_entry(item=component.name, to_warehouse=warehouse, qty=100, rate=100)
		bundle = make_item(properties={"is_stock_item": 0}).name
		bundle_doc = frappe.get_doc({"doctype": "Product Bundle", "new_item_code": bundle})
		bundle_doc.append("items", {"item_code": component.name, "qty": 1, "uom": "Box"})
		bundle_doc.insert()
		bundle_doc.submit()

		delivery_note = create_delivery_note(item_code=bundle, warehouse=warehouse, qty=2)  # 20 Nos
		next(row for row in component.uoms if row.uom == "Box").conversion_factor = 12
		component.save()

		return_note = make_sales_return(delivery_note.name)
		return_note.submit()
		self.assertEqual(return_note.packed_items[0].qty, -20)

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

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	def test_sales_invoice_return_rows_share_the_original_row_qty(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

		self.assert_split_return_over_original_qty_is_rejected(create_sales_invoice(qty=10))

	@ERPNextTestSuite.change_settings("Buying Settings", {"allow_multiple_items": 1})
	def test_purchase_invoice_return_rows_share_the_original_row_qty(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice

		self.assert_split_return_over_original_qty_is_rejected(make_purchase_invoice(qty=10))

	def assert_split_return_over_original_qty_is_rejected(self, original):
		from erpnext.controllers.sales_and_purchase_return import StockOverReturnError, make_return_doc

		return_doc = make_return_doc(original.doctype, original.name)
		return_doc.items[0].qty = -6
		return_doc.append("items", return_doc.items[0].as_dict(no_default_fields=True))

		self.assertRaises(StockOverReturnError, return_doc.insert)


def get_posted_stock_qty(doc):
	"""Stock qty the stock ledger moved for `doc`."""
	actual_qty = frappe.get_all(
		"Stock Ledger Entry", filters={"voucher_no": doc.name, "is_cancelled": 0}, pluck="actual_qty"
	)
	return flt(sum(actual_qty), frappe.get_precision("Stock Ledger Entry", "actual_qty"))


def make_box_item(conversion_factor):
	from erpnext.stock.doctype.item.test_item import make_item

	return make_item(
		properties={
			"is_stock_item": 1,
			"stock_uom": "Kg",
			"uoms": [
				{"uom": "Kg", "conversion_factor": 1},
				{"uom": "Box", "conversion_factor": conversion_factor},
			],
		}
	).name


def make_box_delivery_note(conversion_factor, delivery_rows=1):
	"""Deliver 3 Box over `delivery_rows` rows."""
	from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
	from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

	item_code = make_box_item(conversion_factor)
	make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=20, basic_rate=100)
	dn = create_delivery_note(item_code=item_code, qty=3 // delivery_rows, do_not_submit=True)
	for _ in range(delivery_rows - 1):
		dn.append("items", dict(dn.items[0].as_dict(), name=None))
	for row in dn.items:
		row.uom, row.conversion_factor = "Box", conversion_factor
	dn.submit()
	return dn


def make_split_return_of_box_item(conversion_factor, delivery_rows):
	from erpnext.stock.doctype.delivery_note.mapper import make_sales_return

	dn = make_box_delivery_note(conversion_factor, delivery_rows)
	return_dn = make_sales_return(dn.name)
	if delivery_rows == 1:
		return_dn.items[0].qty = -1
		for _ in range(2):
			return_dn.append("items", dict(return_dn.items[0].as_dict(), name=None, dn_detail=None))
	return return_dn


def make_bundle_with_component(component_qty, bundle_properties=None):
	from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
	from erpnext.stock.doctype.item.test_item import make_item
	from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

	component = make_item(properties={"is_stock_item": 1}).name
	bundle = make_item(properties={"is_stock_item": 0, **(bundle_properties or {})}).name
	make_product_bundle(bundle, [component], qty=component_qty)
	make_stock_entry(item_code=component, target="_Test Warehouse - _TC", qty=20, basic_rate=100)
	return component, bundle
