# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _, msgprint

from erpnext.stock.services.base_stock_gl_composer import BaseStockGLComposer


class StockReconciliationGLComposer(BaseStockGLComposer):
	"""GL composer for Stock Reconciliation.

	SR carries its own expense_account and cost_center which are passed as
	defaults into the base stock GL composition loop. It synthesises one voucher
	detail per stock ledger entry (SR has no ``items`` table with expense rows)
	and posts the difference to a balance-sheet account, so P&L enforcement is
	off.
	"""

	enforce_pl_expense_account = False

	def compose(self, inventory_account_map: dict | None = None) -> list:
		doc = self.doc
		if not doc.cost_center:
			msgprint(_("Please enter Cost Center"), raise_exception=1)
		return super().compose(inventory_account_map, doc.expense_account, doc.cost_center)

	def get_voucher_details(self, default_expense_account, default_cost_center, sle_map):
		is_opening = "Yes" if self.doc.purpose == "Opening Stock" else "No"
		return [
			frappe._dict(
				{
					"name": voucher_detail_no,
					"expense_account": default_expense_account,
					"cost_center": default_cost_center,
					"is_opening": is_opening,
				}
			)
			for voucher_detail_no in sle_map
		]
