# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import POSInvoiceTestMixin, create_pos_invoice
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt


class TestPOSInvoiceMerging(POSInvoiceTestMixin):
	def clear_pos_data(self):
		frappe.db.sql("delete from `tabPOS Opening Entry`;")
		frappe.db.sql("delete from `tabPOS Closing Entry`;")
		frappe.db.sql("delete from `tabPOS Invoice`;")

	def setUp(self):
		self.clear_pos_data()
		super().setUp()

		from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry

		self.opening_entry = create_opening_entry(self.pos_profile, self.test_user.name)

	def test_merging_into_sales_invoice_with_discount(self):
		from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import (
			make_closing_entry_from_opening,
		)
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import (
			init_user_and_profile,
		)
		from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import (
			consolidate_pos_invoices,
		)

		frappe.db.sql("delete from `tabPOS Invoice`")
		test_user, pos_profile = init_user_and_profile()
		pos_inv = create_pos_invoice(rate=300, additional_discount_percentage=10, do_not_submit=1)
		pos_inv.append("payments", {"mode_of_payment": "Cash", "amount": 270})
		pos_inv.save()
		pos_inv.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "amount": 3200})
		pos_inv2.save()
		pos_inv2.submit()

		closing_entry = make_closing_entry_from_opening(self.opening_entry)
		consolidate_pos_invoices(closing_entry=closing_entry)  # does DB commit

		pos_inv.load_from_db()
		rounded_total = frappe.db.get_value("Sales Invoice", pos_inv.consolidated_invoice, "rounded_total")
		self.assertEqual(rounded_total, 3470)

	def test_merging_into_sales_invoice_with_discount_and_inclusive_tax(self):
		from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import (
			make_closing_entry_from_opening,
		)
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import (
			init_user_and_profile,
		)
		from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import (
			consolidate_pos_invoices,
		)

		frappe.db.sql("delete from `tabPOS Invoice`")
		test_user, pos_profile = init_user_and_profile()
		pos_inv = create_pos_invoice(rate=300, do_not_submit=1)
		pos_inv.append("payments", {"mode_of_payment": "Cash", "amount": 300})
		pos_inv.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Service Tax",
				"rate": 14,
				"included_in_print_rate": 1,
			},
		)
		pos_inv.save()
		pos_inv.submit()

		pos_inv2 = create_pos_invoice(rate=300, qty=2, do_not_submit=1)
		pos_inv2.additional_discount_percentage = 10
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "amount": 540})
		pos_inv2.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Service Tax",
				"rate": 14,
				"included_in_print_rate": 1,
			},
		)
		pos_inv2.save()
		pos_inv2.submit()

		self.closing_entry = make_closing_entry_from_opening(self.opening_entry)
		consolidate_pos_invoices(closing_entry=self.closing_entry)  # does DB commit

		pos_inv.load_from_db()
		rounded_total = frappe.db.get_value("Sales Invoice", pos_inv.consolidated_invoice, "rounded_total")
		self.assertEqual(rounded_total, 840)

	def test_merging_with_validate_selling_price(self):
		from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import (
			make_closing_entry_from_opening,
		)
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import (
			init_user_and_profile,
		)
		from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import (
			consolidate_pos_invoices,
		)

		if not frappe.db.get_single_value("Selling Settings", "validate_selling_price"):
			frappe.db.set_single_value("Selling Settings", "validate_selling_price", 1)

		item = "Test Selling Price Validation"
		make_item(item, {"is_stock_item": 1})
		make_purchase_receipt(item_code=item, warehouse="_Test Warehouse - _TC", qty=1, rate=300)
		frappe.db.sql("delete from `tabPOS Invoice`")
		test_user, pos_profile = init_user_and_profile()
		pos_inv = create_pos_invoice(item=item, rate=300, do_not_submit=1)
		pos_inv.append("payments", {"mode_of_payment": "Cash", "amount": 300})
		pos_inv.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Service Tax",
				"rate": 14,
				"included_in_print_rate": 1,
			},
		)
		self.assertRaises(frappe.ValidationError, pos_inv.submit)

		pos_inv2 = create_pos_invoice(item=item, rate=400, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "amount": 400})
		pos_inv2.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Service Tax",
				"rate": 14,
				"included_in_print_rate": 1,
			},
		)
		pos_inv2.save()
		pos_inv2.submit()

		self.closing_entry = make_closing_entry_from_opening(self.opening_entry)
		consolidate_pos_invoices(closing_entry=self.closing_entry)  # does DB commit

		pos_inv2.load_from_db()
		rounded_total = frappe.db.get_value("Sales Invoice", pos_inv2.consolidated_invoice, "rounded_total")
		self.assertEqual(rounded_total, 400)
