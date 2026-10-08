# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.utils import cint

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice, make_sales_return
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestDeliveryNoteInvoiceStockDefaults(ERPNextTestSuite):
	def setUp(self) -> None:
		self.load_test_records("Stock Entry")
		make_property_setter("Sales Invoice", "update_stock", "default", "1", "Check")
		# tearDown rolls back the Property Setter; also discard its cached metadata afterwards.
		self.addCleanup(frappe.clear_cache, doctype="Sales Invoice")
		make_stock_entry(target="_Test Warehouse - _TC", qty=10, basic_rate=100)
		self.delivery_note = create_delivery_note(qty=2)

	def test_conversion_overrides_default_without_posting_stock_again(self) -> None:
		self.assertEqual(cint(frappe.new_doc("Sales Invoice").update_stock), 1)
		invoice = make_sales_invoice(self.delivery_note.name)
		self.assertFalse(invoice.is_pos)
		self.assertFalse(invoice.update_stock)
		self.assertEqual(invoice.items[0].dn_detail, self.delivery_note.items[0].name)
		invoice.insert()
		invoice.submit()
		self.assertFalse(frappe.db.exists("Stock Ledger Entry", {"voucher_no": invoice.name}))
		self.assertEqual(cint(frappe.new_doc("Sales Invoice").update_stock), 1)

	def test_direct_invoice_can_still_update_stock(self) -> None:
		default = cint(frappe.new_doc("Sales Invoice").update_stock)
		invoice = create_sales_invoice(update_stock=default)
		self.assertTrue(invoice.update_stock)
		self.assertTrue(frappe.db.exists("Stock Ledger Entry", {"voucher_no": invoice.name}))

	def test_fetch_into_empty_draft_and_multiple_delivery_notes(self) -> None:
		invoice = frappe.new_doc("Sales Invoice")
		invoice = make_sales_invoice(self.delivery_note.name, target_doc=invoice.as_json())
		other_delivery_note = create_delivery_note()
		invoice = make_sales_invoice(other_delivery_note.name, target_doc=invoice.as_json())
		self.assertFalse(invoice.update_stock)
		self.assertEqual(
			{item.delivery_note for item in invoice.items},
			{self.delivery_note.name, other_delivery_note.name},
		)
		invoice.insert()
		invoice.submit()

	def test_fetch_rejects_unlinked_stock_items(self) -> None:
		invoice = create_sales_invoice(do_not_save=True, update_stock=1)
		with self.assertRaisesRegex(frappe.ValidationError, "not linked to a Delivery Note"):
			make_sales_invoice(self.delivery_note.name, target_doc=invoice.as_json())
		self.assertEqual(invoice.update_stock, 1)

	def test_fetch_rejects_unlinked_stock_bundle(self) -> None:
		parent = make_item("_Test DN Mapping Bundle", {"is_stock_item": 0}).name
		make_product_bundle(parent, ["_Test Item"])
		invoice = create_sales_invoice(item_code=parent, do_not_save=True, update_stock=1)
		with self.assertRaisesRegex(frappe.ValidationError, "not linked to a Delivery Note"):
			make_sales_invoice(self.delivery_note.name, target_doc=invoice.as_json())

	def test_fetch_allows_service_items(self) -> None:
		service = make_item("_Test DN Mapping Service", {"is_stock_item": 0}).name
		invoice = create_sales_invoice(item_code=service, do_not_save=True, update_stock=1)
		invoice = make_sales_invoice(self.delivery_note.name, target_doc=invoice.as_json())
		self.assertFalse(invoice.update_stock)
		self.assertEqual(len(invoice.items), 2)
		invoice.insert()
		invoice.submit()

	def test_fetch_preserves_intentionally_non_stock_updating_invoice(self) -> None:
		invoice = create_sales_invoice(do_not_save=True, update_stock=0)
		invoice = make_sales_invoice(self.delivery_note.name, target_doc=invoice.as_json())
		self.assertFalse(invoice.update_stock)
		self.assertEqual(len(invoice.items), 2)

	def test_fetch_without_billable_rows_preserves_stock_updates(self) -> None:
		billed_invoice = make_sales_invoice(self.delivery_note.name)
		billed_invoice.insert()
		billed_invoice.submit()
		invoice = create_sales_invoice(do_not_save=True, update_stock=1)
		invoice = make_sales_invoice(self.delivery_note.name, target_doc=invoice.as_json())
		self.assertTrue(invoice.update_stock)
		self.assertEqual(len(invoice.items), 1)
		self.assertFalse(invoice.items[0].delivery_note)

	def test_partial_billing_keeps_stock_updates_disabled(self) -> None:
		invoice = make_sales_invoice(self.delivery_note.name)
		invoice.items[0].qty = 1
		invoice.insert()
		invoice.submit()
		remaining_invoice = make_sales_invoice(self.delivery_note.name)
		self.assertEqual(remaining_invoice.items[0].qty, 1)
		self.assertFalse(remaining_invoice.update_stock)
		remaining_invoice.insert()
		remaining_invoice.submit()

	def test_return_delivery_note_does_not_receive_stock_again(self) -> None:
		return_note = make_sales_return(self.delivery_note.name)
		return_note.insert()
		return_note.submit()
		credit_note = make_sales_invoice(return_note.name)
		self.assertTrue(credit_note.is_return)
		self.assertFalse(credit_note.update_stock)
		credit_note.insert()
		credit_note.submit()
		self.assertFalse(frappe.db.exists("Stock Ledger Entry", {"voucher_no": credit_note.name}))

	def test_validation_still_rejects_explicit_stock_updates(self) -> None:
		invoice = make_sales_invoice(self.delivery_note.name)
		invoice.update_stock = 1
		with self.assertRaisesRegex(frappe.ValidationError, "Stock cannot be updated"):
			invoice.insert()
