# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestSalesAndPurchaseReturn(ERPNextTestSuite):
	@staticmethod
	def _cancel_and_delete(doctype, name):
		if not frappe.db.exists(doctype, name):
			return
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc(doctype, name, force=1)

	def test_return_qty_is_checked_when_only_qty_changes(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=100)
		dn = create_delivery_note(qty=5)

		return_dn = make_sales_return(dn.name)
		return_dn.items[0].qty = -50

		self.assertRaises(frappe.ValidationError, return_dn.insert)

	def test_delivery_note_return_row_without_reference_is_limited_to_delivered_qty(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
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
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
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
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
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
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		component, bundle = make_bundle_with_component(component_qty=10)
		dn = create_delivery_note(item_code=bundle, qty=1)
		create_delivery_note(is_return=1, return_against=dn.name, item_code=component, qty=-5)

		self.assertRaises(frappe.ValidationError, make_sales_return(dn.name).insert)

	def test_bundle_return_keeps_order_qty_after_component_uom_change(self):
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
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
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
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
		self.addCleanup(self._cancel_and_delete, "Purchase Invoice", pi.name)

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
		self.addCleanup(self._cancel_and_delete, "Purchase Invoice", pi.name)

		return_pi = make_purchase_invoice(
			item_name="_Test Item",
			is_return=1,
			return_against=pi.name,
			qty=0,
			do_not_save=True,
		)
		return_pi.items[0].item_code = ""

		self.assertRaises(frappe.ValidationError, return_pi.save)

	def test_purchase_return_from_another_warehouse_needs_the_receipt_stock(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item("_Test FIFO Return Warehouse Item", {"valuation_method": "FIFO"}).name
		receipt_warehouse, other_warehouse = "_Test Warehouse - _TC", "_Test Warehouse 1 - _TC"
		make_stock_entry(item_code=item, target=other_warehouse, qty=10, basic_rate=100)
		pr = make_purchase_receipt(item_code=item, warehouse=receipt_warehouse, qty=10, rate=300)

		def make_return():
			return_pr = make_return_doc("Purchase Receipt", pr.name)
			return_pr.items[0].update({"qty": -5, "received_qty": -5, "warehouse": other_warehouse})
			return return_pr.insert()

		# the other warehouse holds stock at 100 only
		self.assertRaisesRegex(frappe.ValidationError, "does not hold enough", make_return().submit)

		make_stock_entry(item_code=item, source=receipt_warehouse, target=other_warehouse, qty=5)
		return_pr = make_return()
		return_pr.submit()
		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_no": return_pr.name, "is_cancelled": 0},
			"stock_value_difference",
		)
		self.assertEqual(stock_value_difference, -1500)

	def test_purchase_return_from_another_warehouse_counts_stock_uom_at_factor_one(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item("_Test FIFO Return Stock UOM Factor Item", {"valuation_method": "FIFO"}).name
		receipt_warehouse, other_warehouse = "_Test Warehouse - _TC", "_Test Warehouse 1 - _TC"
		make_stock_entry(item_code=item, target=other_warehouse, qty=10, basic_rate=100)
		pr = make_purchase_receipt(item_code=item, warehouse=receipt_warehouse, qty=10, rate=300)
		make_stock_entry(item_code=item, source=receipt_warehouse, target=other_warehouse, qty=5)

		return_pr = make_return_doc("Purchase Receipt", pr.name)
		# the factor is reset to 1 later in validate, so the row takes 10, not 5
		return_pr.items[0].update(
			{"qty": -10, "received_qty": -10, "warehouse": other_warehouse, "conversion_factor": 0.5}
		)

		self.assertRaisesRegex(frappe.ValidationError, "does not hold enough", return_pr.submit)

	def test_purchase_return_from_another_receipt_row_warehouse_needs_the_stock_of_both_rows(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item("_Test FIFO Return Two Warehouses Item", {"valuation_method": "FIFO"}).name
		warehouse, other_warehouse = "_Test Warehouse - _TC", "_Test Warehouse 1 - _TC"
		make_stock_entry(item_code=item, target=warehouse, qty=5, basic_rate=100)
		pr = make_purchase_receipt(item_code=item, warehouse=warehouse, qty=5, rate=300, do_not_submit=True)
		pr.append("items", {**pr.items[0].as_dict(), "name": None, "idx": None, "warehouse": other_warehouse})
		pr.submit()

		return_pr = make_return_doc("Purchase Receipt", pr.name)
		for row in return_pr.items:
			row.warehouse = warehouse

		# both rows take the 5 @ 300 the first row received
		self.assertRaisesRegex(frappe.ValidationError, "does not hold enough", return_pr.insert().submit)

	def test_purchase_return_row_added_by_hand_needs_the_receipt_stock(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item = make_item("_Test FIFO Return Row By Hand Item", {"valuation_method": "FIFO"}).name
		other_warehouse = "_Test Warehouse 1 - _TC"
		make_stock_entry(item_code=item, target=other_warehouse, qty=10, basic_rate=100)
		pr = make_purchase_receipt(item_code=item, warehouse="_Test Warehouse - _TC", qty=10, rate=300)

		return_pr = make_return_doc("Purchase Receipt", pr.name)
		return_pr.items[0].update(
			{"qty": -5, "received_qty": -5, "warehouse": other_warehouse, "purchase_receipt_item": None}
		)

		self.assertRaisesRegex(frappe.ValidationError, "does not hold enough", return_pr.insert().submit)

	def test_delivery_note_zero_qty_return_is_rejected(self):
		# A return with every item at qty 0 moves no stock and no value, so it must be
		# rejected the same way a return with no items at all would be.
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		se = make_stock_entry(item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=100)
		self.addCleanup(self._cancel_and_delete, "Stock Entry", se.name)

		dn = create_delivery_note(qty=5)
		self.addCleanup(self._cancel_and_delete, "Delivery Note", dn.name)

		return_dn = make_sales_return(dn.name)
		return_dn.items[0].qty = 0

		self.assertRaises(frappe.ValidationError, return_dn.insert)

	def test_sales_invoice_zero_qty_return_is_rejected(self):
		# Same rule for a standalone (non stock-affecting) Sales Invoice return: qty 0 on
		# every row must be rejected, not silently accepted as a no-op credit note.
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		si = create_sales_invoice(qty=10)
		self.addCleanup(self._cancel_and_delete, "Sales Invoice", si.name)

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
		self.addCleanup(self._cancel_and_delete, "Sales Invoice", si.name)

		first_return = make_return_doc(si.doctype, si.name)
		first_return.items[0].qty = -24
		first_return.save().submit()
		self.addCleanup(self._cancel_and_delete, "Sales Invoice", first_return.name)

		second_return = make_return_doc(si.doctype, si.name)
		self.assertEqual(second_return.items[0].qty, -24)
		second_return.save().submit()
		self.addCleanup(self._cancel_and_delete, "Sales Invoice", second_return.name)

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

	def test_return_in_another_uom_is_checked_per_stock_uom(self):
		"""Return rates and quantities are compared per stock UOM, whatever UOM the return row uses."""
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item_code = make_item(
			properties={
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"uoms": [{"uom": "Box", "conversion_factor": 12}],
			}
		).name
		make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=24, basic_rate=100)

		def submit_one_box(doc):
			doc.items[0].update(
				{"uom": "Box", "conversion_factor": 12, "qty": 1, "rate": 2400, "price_list_rate": 2400}
			)
			return doc.submit()

		def return_in_nos(original, qty, rate):
			return_doc = make_return_doc(original.doctype, original.name)
			return_doc.items[0].update(
				{"uom": "Nos", "conversion_factor": 1, "qty": qty, "rate": rate, "price_list_rate": rate}
			)
			return return_doc

		dn = submit_one_box(create_delivery_note(item_code=item_code, do_not_submit=True))
		self.assertRaises(frappe.ValidationError, return_in_nos(dn, -5, 2400).insert)
		return_in_nos(dn, -5, 200).submit()
		# what is left is 7 Nos, which a whole number Box cannot hold, so it maps in stock UOM
		rest = make_return_doc(dn.doctype, dn.name)
		self.assertEqual((rest.items[0].uom, rest.items[0].qty, rest.items[0].rate), ("Nos", -7, 200))
		rest.insert()

		si = submit_one_box(create_sales_invoice(item_code=item_code, do_not_submit=True))
		return_in_nos(si, -5, 200).insert()
		self.assertRaises(frappe.ValidationError, return_in_nos(si, -1, 2400).insert)

	def test_credit_note_qty_is_checked_in_return_row_uom(self):
		"""A tiny conversion factor must not round an over-credit away in stock UOM."""
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.controllers.sales_and_purchase_return import StockOverReturnError, make_return_doc
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(
			properties={"stock_uom": "Nos", "uoms": [{"uom": "_Test UOM 1", "conversion_factor": 0.000001}]}
		).name
		si = create_sales_invoice(item_code=item_code, do_not_submit=True)
		si.items[0].update({"uom": "_Test UOM 1", "conversion_factor": 0.000001, "qty": 1})
		si.submit()

		credit_note = make_return_doc(si.doctype, si.name)
		credit_note.items[0].qty = -100
		self.assertRaises(StockOverReturnError, credit_note.insert)

	def test_credit_note_in_a_larger_uom_cannot_round_the_billed_qty_up(self):
		"""0.6 of a qty step billed in the return row's UOM must not round up to allow a whole step."""
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.controllers.sales_and_purchase_return import StockOverReturnError, make_return_doc
		from erpnext.stock.doctype.item.test_item import make_item

		# the quantities are fractions of a qty step
		for uom in ("Nos", "_Test UOM 1"):
			frappe.db.set_value("UOM", uom, "must_be_whole_number", 0)
		item_code = make_item(
			properties={"stock_uom": "Nos", "uoms": [{"uom": "_Test UOM 1", "conversion_factor": 10}]}
		).name
		si = create_sales_invoice(item_code=item_code, do_not_submit=True)
		step = 10 ** -si.items[0].precision("qty")
		si.items[0].qty = 6 * step
		si.submit()

		credit_note = make_return_doc(si.doctype, si.name)
		credit_note.items[0].update({"uom": "_Test UOM 1", "conversion_factor": 10, "qty": -step})
		self.assertRaises(StockOverReturnError, credit_note.insert)

	def test_return_rate_ceiling_holds_for_large_conversion_factor(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item_code = make_item(
			properties={
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"uoms": [{"uom": "Box", "conversion_factor": 1000}],
			}
		).name
		make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=1000, basic_rate=1)

		dn = create_delivery_note(item_code=item_code, do_not_submit=True)
		dn.items[0].update(
			{"uom": "Box", "conversion_factor": 1000, "qty": 1, "rate": 1, "price_list_rate": 1}
		)
		dn.submit()

		return_dn = make_return_doc(dn.doctype, dn.name)
		return_dn.items[0].update({"rate": 4, "price_list_rate": 4})
		self.assertRaises(frappe.ValidationError, return_dn.insert)

	def test_purchase_return_maps_after_accepted_and_rejected_warehouse_returns(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_return,
			make_purchase_return_against_rejected_warehouse,
		)
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		pr = make_purchase_receipt(qty=5, rejected_qty=5)
		accepted_return = make_purchase_return(pr.name)
		accepted_return.items[0].update({"qty": -2, "rejected_qty": -1, "received_qty": -3})
		accepted_return.submit()

		rejected_return = make_purchase_return_against_rejected_warehouse(pr.name)
		rejected_return.items[0].update({"qty": -1, "received_qty": -1})
		rejected_return.submit()

		self.assertEqual(make_purchase_return(pr.name).items[0].qty, -3)

	def test_purchase_return_maps_rejected_qty_after_return_in_another_uom(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_return,
			make_purchase_return_against_rejected_warehouse,
		)
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		item_code = make_item(
			properties={
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"uoms": [{"uom": "Box", "conversion_factor": 12}],
			}
		).name
		pr = make_purchase_receipt(
			item_code=item_code,
			uom="Box",
			stock_uom="Nos",
			conversion_factor=12,
			qty=2,
			rejected_qty=2,
			rate=1200,
		)
		first_return = make_purchase_return(pr.name)
		first_return.items[0].update(
			{"uom": "Nos", "conversion_factor": 1, "qty": -12, "rejected_qty": -12, "received_qty": -24}
		)
		first_return.submit()

		# 12 Nos accepted and 12 Nos rejected are left, mapped in the receipt row's UOM
		self.assertEqual(make_purchase_return(pr.name).items[0].rejected_qty, -1)
		self.assertEqual(make_purchase_return_against_rejected_warehouse(pr.name).items[0].qty, -1)

	def test_purchase_invoice_return_maps_received_qty_after_return_in_another_uom(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(
			properties={
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"uoms": [{"uom": "Box", "conversion_factor": 12}],
			}
		).name
		pi = make_purchase_invoice(item_code=item_code, uom="Nos", update_stock=1, do_not_save=True)
		pi.items[0].update(
			{"uom": "Box", "conversion_factor": 12, "qty": 10, "received_qty": 10, "rate": 120}
		)
		pi.submit()

		first_return = make_return_doc(pi.doctype, pi.name)
		first_return.items[0].update(
			{"uom": "Nos", "conversion_factor": 1, "qty": -12, "received_qty": -12, "rate": 10}
		)
		first_return.submit()

		# 108 Nos are left, mapped in the invoiced row's UOM, which must be whole
		second_return = make_return_doc(pi.doctype, pi.name)
		self.assertEqual(second_return.items[0].qty, -9)
		self.assertEqual(second_return.items[0].received_qty, -9)
		second_return.insert()


def make_split_return_of_box_item(conversion_factor, delivery_rows):
	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
	from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
	from erpnext.stock.doctype.item.test_item import make_item
	from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

	item_code = make_item(
		properties={
			"is_stock_item": 1,
			"stock_uom": "Kg",
			"uoms": [
				{"uom": "Kg", "conversion_factor": 1},
				{"uom": "Box", "conversion_factor": conversion_factor},
			],
		}
	).name
	make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=20, basic_rate=100)
	dn = create_delivery_note(item_code=item_code, qty=3 // delivery_rows, do_not_submit=True)
	for _ in range(delivery_rows - 1):
		dn.append("items", dict(dn.items[0].as_dict(), name=None))
	for row in dn.items:
		row.uom, row.conversion_factor = "Box", conversion_factor
	dn.submit()

	return_dn = make_sales_return(dn.name)
	if delivery_rows == 1:
		return_dn.items[0].qty = -1
		for _ in range(2):
			return_dn.append("items", dict(return_dn.items[0].as_dict(), name=None, dn_detail=None))
	return return_dn


def make_bundle_with_component(component_qty):
	from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
	from erpnext.stock.doctype.item.test_item import make_item
	from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

	component = make_item(properties={"is_stock_item": 1}).name
	bundle = make_item(properties={"is_stock_item": 0}).name
	make_product_bundle(bundle, [component], qty=component_qty)
	make_stock_entry(item_code=component, target="_Test Warehouse - _TC", qty=20, basic_rate=100)
	return component, bundle
