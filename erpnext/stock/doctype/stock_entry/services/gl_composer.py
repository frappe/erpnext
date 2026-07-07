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

		if doc.purpose in ("Repack", "Manufacture"):
			self._append_manufacturing_variance_gl_entries(gl_entries, inventory_account_map)
		elif doc.purpose == "Material Receipt":
			self._append_receipt_variance_gl_entries(gl_entries)

		return process_gl_map(gl_entries, from_repost=frappe.flags.through_repost_item_valuation)

	def _append_manufacturing_variance_gl_entries(
		self, gl_entries: list, inventory_account_map: dict
	) -> None:
		"""For Standard Cost finished goods produced via Manufacture/Repack, stock is booked at the item's
		standard rate, while the entry consumes raw-material (plus additional/landed) cost. The difference
		is a manufacturing variance and is reclassified from the finished good's expense account to the
		Manufacturing Variance account (mirrors Purchase Price Variance on a Purchase Receipt)."""
		precision = self.get_debit_field_precision()
		# Reuse the SLE map the base composer already fetched in compose() to avoid a second identical query.
		sle_map = self._sle_map

		from erpnext.stock.doctype.item_standard_cost.item_standard_cost import (
			get_manufacturing_variance_account,
		)

		for d in self.doc.get("items"):
			variance = self._get_finished_good_variance(d, sle_map, precision)
			if variance:
				account = get_manufacturing_variance_account(d.item_code, self.doc.company)
				remarks = self.doc.get("remarks") or _("Manufacturing Variance for {0}").format(d.item_code)
				self._append_standard_cost_variance_pair(
					gl_entries, d, variance, account, remarks, inventory_account_map
				)

	def _append_receipt_variance_gl_entries(self, gl_entries: list) -> None:
		"""For a Standard Cost item received via Material Receipt, stock is booked at the item's standard
		rate while the row may carry a manually-set basic rate plus additional/landed cost. The gap
		between that intended cost and the standard value is a purchase price variance, reclassified from
		the item's expense account to the Purchase Price Variance account."""
		from erpnext.stock.doctype.item_standard_cost.item_standard_cost import (
			get_purchase_price_variance_account,
		)

		precision = self.get_debit_field_precision()
		sle_map = self._sle_map

		for d in self.doc.get("items"):
			variance = self._get_receipt_variance(d, sle_map, precision)
			if variance:
				account = get_purchase_price_variance_account(d.item_code, self.doc.company)
				remarks = self.doc.get("remarks") or _("Purchase Price Variance for {0}").format(d.item_code)
				self._append_standard_cost_variance_pair(gl_entries, d, variance, account, remarks)

	def _get_receipt_variance(self, item, sle_map, precision) -> float:
		"""Purchase price variance for a Standard Cost item on a Material Receipt: the gap between the full
		computed incoming cost (basic amount + additional cost + LCV, i.e. ``amount``) and the standard
		value booked into stock. 0 for anything that is not a plain Standard Cost receipt row."""
		from erpnext.stock.utils import get_valuation_method

		if not item.t_warehouse or item.s_warehouse:
			return 0.0

		if (
			item.get("is_finished_item")
			or item.get("secondary_item_type")
			or item.get("is_legacy_scrap_item")
		):
			return 0.0

		if get_valuation_method(item.item_code, self.doc.company) != "Standard Cost":
			return 0.0

		standard_value = sum(
			flt(sle.stock_value_difference) for sle in sle_map.get(item.name, []) if flt(sle.actual_qty) > 0
		)

		return flt(flt(item.amount) - standard_value, precision)

	def _get_finished_good_variance(self, item, sle_map, precision) -> float:
		"""Manufacturing variance for a Standard Cost finished good: the gap between the full computed
		incoming cost (raw-material share + additional cost + LCV, i.e. ``amount``) and the standard value
		actually booked into stock. Positive = consumed more than standard (unfavorable). 0 for anything
		that is not a Standard Cost finished good."""
		from erpnext.stock.utils import get_valuation_method

		if not item.is_finished_item or not item.t_warehouse:
			return 0.0

		if get_valuation_method(item.item_code, self.doc.company) != "Standard Cost":
			return 0.0

		# Value actually booked into stock for this finished good = qty * standard rate.
		standard_value = sum(
			flt(sle.stock_value_difference) for sle in sle_map.get(item.name, []) if flt(sle.actual_qty) > 0
		)

		return flt(flt(item.amount) - standard_value, precision)

	def _append_standard_cost_variance_pair(
		self,
		gl_entries: list,
		item,
		variance: float,
		variance_account: str,
		remarks: str,
		inventory_account_map: dict | None = None,
	) -> None:
		"""Reclassify ``variance`` from the item's expense account to the given variance account,
		restoring the expense account to the value it would carry without Standard Cost."""
		doc = self.doc
		cost_center = item.cost_center or frappe.get_cached_value("Company", doc.company, "cost_center")
		project = item.project or doc.get("project")

		inventory_account = None
		if inventory_account_map:
			inventory_account = doc.get_inventory_account_dict(item, inventory_account_map, "t_warehouse")[
				"account"
			]

		gl_entries.append(
			self.get_gl_dict(
				{
					"account": variance_account,
					"against": item.expense_account,
					"cost_center": cost_center,
					"remarks": remarks,
					"debit": variance,
					"project": project,
				},
				item=item,
			)
		)
		gl_entries.append(
			self.get_gl_dict(
				{
					"account": item.expense_account,
					"against": inventory_account or variance_account,
					"cost_center": cost_center,
					"remarks": remarks,
					"debit": -1 * variance,
					"project": project,
				},
				item=item,
			)
		)

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

	def get_valuation_method(self, item_code: str) -> str:
		from erpnext.stock.utils import get_valuation_method

		return get_valuation_method(item_code, self.doc.company)

	def _append_additional_cost_gl_entries(
		self, gl_entries: list, item_account_wise_additional_cost: dict
	) -> None:
		doc = self.doc
		precision = self.get_debit_field_precision()

		for d in doc.get("items"):
			for account, amount in item_account_wise_additional_cost.get((d.item_code, d.name), {}).items():
				if not amount:
					continue

				amount["amount"] = flt(amount["amount"], precision)
				amount["base_amount"] = flt(amount["base_amount"], precision)

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

				if self.get_valuation_method(d.item_code) == "Standard Cost":
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": d.expense_account,
								"against": account,
								"cost_center": d.cost_center,
								"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
								"debit": flt(amount["base_amount"]),
							},
							item=d,
						)
					)

				else:
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": d.expense_account,
								"against": account,
								"cost_center": d.cost_center,
								"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
								"credit": -1 * flt(amount["base_amount"]),
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
