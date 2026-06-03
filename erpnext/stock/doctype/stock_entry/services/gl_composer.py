# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.general_ledger import process_gl_map
from erpnext.accounts.utils import get_account_currency
from erpnext.stock.services.base_stock_gl_composer import BaseStockGLComposer


class StockEntryGLComposer(BaseStockGLComposer):
	"""GL composer for Stock Entry.

	Extends the base stock GL loop with additional-cost entries (from the
	``additional_costs`` child table) and landed-cost voucher adjustments.
	"""

	def compose(self, inventory_account_map: dict | None = None) -> list:
		doc = self.doc
		gl_entries = super().compose(inventory_account_map)

		if doc.purpose in ("Repack", "Manufacture"):
			total_basic_amount = sum(flt(t.basic_amount) for t in doc.get("items") if t.is_finished_item)
		else:
			total_basic_amount = sum(flt(t.basic_amount) for t in doc.get("items") if t.t_warehouse)

		divide_based_on = total_basic_amount
		if doc.get("additional_costs") and not total_basic_amount:
			divide_based_on = sum(item.qty for item in doc.get("items"))

		item_account_wise_additional_cost = self._build_additional_cost_per_item_account(
			total_basic_amount, divide_based_on
		)
		if item_account_wise_additional_cost:
			self._append_additional_cost_gl_entries(gl_entries, item_account_wise_additional_cost)

		self._append_lcv_gl_entries(gl_entries, inventory_account_map)

		return process_gl_map(gl_entries, from_repost=frappe.flags.through_repost_item_valuation)

	def _build_additional_cost_per_item_account(
		self, total_basic_amount: float, divide_based_on: float
	) -> dict:
		doc = self.doc
		item_account_wise_additional_cost = {}

		for t in doc.get("additional_costs"):
			for d in doc.get("items"):
				if doc.purpose in ("Repack", "Manufacture") and not d.is_finished_item:
					continue
				elif not d.t_warehouse:
					continue

				item_account_wise_additional_cost.setdefault((d.item_code, d.name), {})
				item_account_wise_additional_cost[(d.item_code, d.name)].setdefault(
					t.expense_account, {"amount": 0.0, "base_amount": 0.0}
				)

				multiply_based_on = d.basic_amount if total_basic_amount else d.qty
				entry = item_account_wise_additional_cost[(d.item_code, d.name)][t.expense_account]
				entry["amount"] += flt(t.amount * multiply_based_on) / divide_based_on
				entry["base_amount"] += flt(t.base_amount * multiply_based_on) / divide_based_on

		return item_account_wise_additional_cost

	def _append_additional_cost_gl_entries(
		self, gl_entries: list, item_account_wise_additional_cost: dict
	) -> None:
		doc = self.doc
		for d in doc.get("items"):
			for account, amount in item_account_wise_additional_cost.get((d.item_code, d.name), {}).items():
				if not amount:
					continue

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": account,
							"against": d.expense_account,
							"cost_center": d.cost_center,
							"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
							"credit_in_account_currency": flt(amount["amount"]),
							"credit": flt(amount["base_amount"]),
						},
						item=d,
					)
				)

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": d.expense_account,
							"against": account,
							"cost_center": d.cost_center,
							"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
							"credit": -1 * amount["base_amount"],
						},
						item=d,
					)
				)

	def _append_lcv_gl_entries(self, gl_entries: list, inventory_account_map: dict) -> None:
		doc = self.doc
		landed_cost_entries = doc.get_item_account_wise_lcv_entries()
		if not landed_cost_entries:
			return

		for item in doc.get("items"):
			if item.s_warehouse:
				continue

			if (item.item_code, item.name) in landed_cost_entries:
				for account, amount in landed_cost_entries[(item.item_code, item.name)].items():
					account_currency = get_account_currency(account)
					credit_amount = (
						flt(amount["base_amount"])
						if (amount["base_amount"] or account_currency != doc.company_currency)
						else flt(amount["amount"])
					)

					_inv_dict = doc.get_inventory_account_dict(item, inventory_account_map, "t_warehouse")
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": account,
								"against": _inv_dict["account"],
								"cost_center": item.cost_center,
								"debit": 0.0,
								"credit": credit_amount,
								"remarks": _("Accounting Entry for LCV in Stock Entry {0}").format(doc.name),
								"credit_in_account_currency": flt(amount["amount"]),
								"account_currency": account_currency,
								"project": item.project,
							},
							item=item,
						)
					)

					account_currency = get_account_currency(item.expense_account)
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": item.expense_account,
								"against": _inv_dict["account"],
								"cost_center": item.cost_center,
								"debit": 0.0,
								"credit": credit_amount * -1,
								"remarks": _("Accounting Entry for LCV in Stock Entry {0}").format(doc.name),
								"debit_in_account_currency": flt(amount["amount"]),
								"account_currency": account_currency,
								"project": item.project,
							},
							item=item,
						)
					)
