# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.patches.v15_0.migrate_old_item_wise_tax_detail_data_to_table import (
	ItemTax,
	compile_docs,
	get_doc_details,
	get_items_for_docs,
)
from erpnext.tests.utils import ERPNextTestSuite

ITEM_COLUMN = ("Purchase Invoice Item", "apply_tds")
PARENT_COLUMN = ("Purchase Invoice", "base_tax_withholding_net_total")


class TestMigrateOldItemWiseTaxDetailData(ERPNextTestSuite):
	def test_withholding_is_allocated_when_legacy_columns_are_missing(self):
		"""Databases without the withholding columns must still spread an Actual TDS row over the items."""
		invoice = self.make_invoice()
		doc = self.compile_invoice(invoice, removed_columns={ITEM_COLUMN, PARENT_COLUMN})

		self.assertEqual({item.apply_tds for item in doc["items"]}, {1})
		self.assertEqual(doc.base_tax_withholding_net_total, 400)
		self.assertEqual(self.allocated_amounts(doc), [-30.0, -10.0])

	def test_withholding_base_skips_exempt_items_when_parent_column_is_missing(self):
		"""Without the parent column the base is the TDS items' total, so exempt items don't dilute it."""
		invoice = self.make_invoice()
		frappe.db.set_value("Purchase Invoice Item", invoice.items[1].name, "apply_tds", 0)
		doc = self.compile_invoice(invoice, removed_columns={PARENT_COLUMN})

		self.assertEqual(doc.base_tax_withholding_net_total, 100)
		self.assertEqual(self.allocated_amounts(doc), [-40.0, 0.0])

	def make_invoice(self):
		invoice = make_purchase_invoice(qty=1, rate=100, do_not_submit=True)
		second_item = frappe.copy_doc(invoice.items[0])
		second_item.update({"item_code": "_Test Item 2", "item_name": "_Test Item 2", "rate": 300})
		invoice.append("items", second_item)
		invoice.items[0].apply_tds = 1
		invoice.items[1].apply_tds = 1
		invoice.submit()
		return invoice

	def compile_invoice(self, invoice, removed_columns):
		has_column = frappe.db.has_column
		with patch.object(
			frappe.db,
			"has_column",
			side_effect=lambda doctype, column: (doctype, column) not in removed_columns
			and has_column(doctype, column),
		):
			items = get_items_for_docs([invoice.name], "Purchase Invoice")
			doc_info = get_doc_details([invoice.name], "Purchase Invoice")

		tds_row = frappe._dict(
			name="tds-row",
			parent=invoice.name,
			parenttype="Purchase Invoice",
			docstatus=1,
			charge_type="Actual",
			account_head="_Test Account Excise Duty - _TC",
			rate=0,
			base_tax_amount_after_discount_amount=40,
			add_deduct_tax="Deduct",
			is_tax_withholding_account=1,
		)
		return next(
			iter(compile_docs(doc_info, [tds_row], items, "Purchase Invoice", "Purchase Taxes and Charges"))
		)

	def allocated_amounts(self, doc):
		return sorted(row.amount for row in ItemTax().get_item_wise_tax_details(doc))
