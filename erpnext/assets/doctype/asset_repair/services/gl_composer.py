# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

import erpnext
from erpnext.accounts.services.base_gl_composer import BaseGLComposer
from erpnext.assets.doctype.asset.asset import get_asset_account


class AssetRepairGLComposer(BaseGLComposer):
	"""GL composer for Asset Repair.

	Builds GL entries for repair cost (per invoice) and consumed stock items
	(sourced from the related Stock Entry).
	"""

	def compose(self) -> list:
		doc = self.doc
		gl_entries = []

		fixed_asset_account = get_asset_account("fixed_asset_account", asset=doc.asset, company=doc.company)
		self._get_gl_entries_for_repair_cost(gl_entries, fixed_asset_account)
		self._get_gl_entries_for_consumed_items(gl_entries, fixed_asset_account)

		return gl_entries

	def _get_gl_entries_for_repair_cost(self, gl_entries: list, fixed_asset_account: str) -> None:
		doc = self.doc
		if flt(doc.repair_cost) <= 0:
			return

		debit_against_account = set()

		for pi in doc.invoices:
			debit_against_account.add(pi.expense_account)
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": pi.expense_account,
						"credit": pi.repair_cost,
						"credit_in_account_currency": pi.repair_cost,
						"against": fixed_asset_account,
						"voucher_type": doc.doctype,
						"voucher_no": doc.name,
						"cost_center": doc.cost_center,
						"posting_date": doc.completion_date,
						"company": doc.company,
					},
					item=doc,
				)
			)

		debit_against_account_str = ", ".join(debit_against_account)
		gl_entries.append(
			self.get_gl_dict(
				{
					"account": fixed_asset_account,
					"debit": doc.repair_cost,
					"debit_in_account_currency": doc.repair_cost,
					"against": debit_against_account_str,
					"voucher_type": doc.doctype,
					"voucher_no": doc.name,
					"cost_center": doc.cost_center,
					"posting_date": doc.completion_date,
					"against_voucher_type": "Asset",
					"against_voucher": doc.asset,
					"company": doc.company,
				},
				item=doc,
			)
		)

	def _get_gl_entries_for_consumed_items(self, gl_entries: list, fixed_asset_account: str) -> None:
		doc = self.doc
		if not doc.get("stock_items"):
			return

		stock_entry_name = frappe.db.get_value("Stock Entry", {"asset_repair": doc.name}, "name")
		stock_entry_items = frappe.get_all(
			"Stock Entry Detail", filters={"parent": stock_entry_name}, fields=["expense_account", "amount"]
		)

		default_expense_account = None
		if not erpnext.is_perpetual_inventory_enabled(doc.company):
			default_expense_account = frappe.get_cached_value(
				"Company", doc.company, "default_expense_account"
			)
			if not default_expense_account:
				frappe.throw(_("Please set default Expense Account in Company {0}").format(doc.company))

		for item in stock_entry_items:
			if flt(item.amount) > 0:
				gl_entries.append(
					self.get_gl_dict(
						{
							"account": item.expense_account or default_expense_account,
							"credit": item.amount,
							"credit_in_account_currency": item.amount,
							"against": fixed_asset_account,
							"voucher_type": doc.doctype,
							"voucher_no": doc.name,
							"cost_center": doc.cost_center,
							"posting_date": doc.completion_date,
							"company": doc.company,
						},
						item=doc,
					)
				)

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": fixed_asset_account,
							"debit": item.amount,
							"debit_in_account_currency": item.amount,
							"against": item.expense_account or default_expense_account,
							"voucher_type": doc.doctype,
							"voucher_no": doc.name,
							"cost_center": doc.cost_center,
							"posting_date": doc.completion_date,
							"against_voucher_type": "Stock Entry",
							"against_voucher": stock_entry_name,
							"company": doc.company,
						},
						item=doc,
					)
				)
