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

REMOVED_COLUMNS = {
	("Purchase Invoice Item", "apply_tds"),
	("Purchase Invoice", "base_tax_withholding_net_total"),
}


class TestMigrateOldItemWiseTaxDetailData(ERPNextTestSuite):
	def test_withholding_is_allocated_when_legacy_columns_are_missing(self):
		"""Databases without the withholding columns must still spread an Actual TDS row over the items."""
		invoice = make_purchase_invoice(qty=1, rate=100, do_not_submit=True)
		second_item = frappe.copy_doc(invoice.items[0])
		second_item.rate = 300
		invoice.append("items", second_item)
		invoice.submit()

		has_column = frappe.db.has_column
		with patch.object(
			frappe.db,
			"has_column",
			side_effect=lambda doctype, column: (doctype, column) not in REMOVED_COLUMNS
			and has_column(doctype, column),
		):
			items = get_items_for_docs([invoice.name], "Purchase Invoice")
			doc_info = get_doc_details([invoice.name], "Purchase Invoice")

		self.assertEqual({item.apply_tds for item in items}, {1})
		self.assertEqual(doc_info[0].base_tax_withholding_net_total, doc_info[0].base_net_total)

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
		doc = next(
			iter(compile_docs(doc_info, [tds_row], items, "Purchase Invoice", "Purchase Taxes and Charges"))
		)
		amounts = sorted(row.amount for row in ItemTax().get_item_wise_tax_details(doc))

		self.assertEqual(amounts, [-30.0, -10.0])
