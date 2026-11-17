# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.doctype.customer.test_customer import create_internal_customer
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestSellingController(ERPNextTestSuite):
	@ERPNextTestSuite.change_settings("Selling Settings", {"validate_selling_price": 1})
	def test_internal_transfer_skips_the_last_purchase_rate_check(self):
		"""An internal transfer moves stock at its valuation rate, below the last purchase rate."""
		item_code = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(item_code=item_code, target="Stores - TCP1", qty=10, basic_rate=89.48)
		frappe.db.set_value("Item", item_code, "last_purchase_rate", 120)

		dn = create_delivery_note(
			item_code=item_code,
			company="_Test Company with perpetual inventory",
			customer="_Test Internal Customer 2",
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			qty=1,
			warehouse="Stores - TCP1",
			target_warehouse="Goods In Transit - TCP1",
		)

		self.assertEqual(dn.docstatus, 1)

	@ERPNextTestSuite.change_settings("Selling Settings", {"validate_selling_price": 1})
	def test_inter_company_sale_keeps_the_last_purchase_rate_check(self):
		item_code = make_item(properties={"is_stock_item": 0}).name
		frappe.db.set_value("Item", item_code, "last_purchase_rate", 120)
		customer = create_internal_customer(
			customer_name="_Test Internal Customer",
			represents_company="_Test Company 1",
			allowed_to_interact_with="Wind Power LLC",
		)

		si = create_sales_invoice(
			item_code=item_code,
			company="Wind Power LLC",
			customer=customer,
			debit_to="Debtors - WP",
			income_account="Sales - WP",
			expense_account="Cost of Goods Sold - WP",
			cost_center="Main - WP",
			currency="USD",
			rate=90,
			do_not_save=True,
		)

		self.assertRaisesRegex(frappe.ValidationError, "last purchase rate", si.save)
