# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.accounts.general_ledger import process_gl_map
from erpnext.accounts.services.base_gl_composer import BaseGLComposer


class BaseStockGLComposer(BaseGLComposer):
	"""Shared GL composition logic for stock vouchers.

	Subclasses override ``compose()`` and call ``super().compose()`` to get the
	warehouse ↔ expense-account GL pairs, then append any doctype-specific
	entries on top.
	"""

	#: Whether the item's expense/difference account must be a 'Profit and Loss'
	#: account. Vouchers that legitimately post the difference to a balance-sheet
	#: account (stock transfers, deliveries, reconciliations) set this to False.
	enforce_pl_expense_account = True

	book_expenses_added_to_stock = False

	def compose(
		self,
		inventory_account_map: dict | None = None,
		default_expense_account: str | None = None,
		default_cost_center: str | None = None,
	) -> list:
		doc = self.doc

		if not inventory_account_map:
			inventory_account_map = doc.get_inventory_account_map()

		sle_map = self._sle_map = doc.get_stock_ledger_details()
		voucher_details = self.get_voucher_details(default_expense_account, default_cost_center, sle_map)

		gl_list = []
		warehouse_with_no_account = []
		precision = self.get_debit_field_precision()

		for item_row in voucher_details:
			sle_list = sle_map.get(item_row.name)
			sle_rounding_diff = 0.0
			if sle_list:
				for sle in sle_list:
					_inv_dict = doc.get_inventory_account_dict(sle, inventory_account_map)

					if _inv_dict.get("account"):
						sle_rounding_diff += flt(sle.stock_value_difference)

						self.check_expense_account(item_row)

						if item_row.get("target_warehouse"):
							_target_wh_inv_dict = doc.get_inventory_account_dict(
								item_row, inventory_account_map, warehouse_field="target_warehouse"
							)
							expense_account = _target_wh_inv_dict["account"]
						else:
							expense_account = item_row.expense_account

						gl_list.append(
							self.get_gl_dict(
								{
									"account": _inv_dict["account"],
									"against": expense_account,
									"cost_center": item_row.cost_center,
									"project": sle.get("project") or item_row.project or doc.get("project"),
									"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
									"debit": flt(sle.stock_value_difference, precision),
									"is_opening": item_row.get("is_opening") or doc.get("is_opening") or "No",
								},
								_inv_dict["account_currency"],
								item=item_row,
							)
						)

						gl_list.append(
							self.get_gl_dict(
								{
									"account": expense_account,
									"against": _inv_dict["account"],
									"cost_center": item_row.cost_center,
									"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
									"debit": -1 * flt(sle.stock_value_difference, precision),
									"project": sle.get("project")
									or item_row.get("project")
									or doc.get("project"),
									"is_opening": item_row.get("is_opening") or doc.get("is_opening") or "No",
								},
								item=item_row,
							)
						)
					elif sle.warehouse not in warehouse_with_no_account:
						warehouse_with_no_account.append(sle.warehouse)

			if abs(sle_rounding_diff) > (1.0 / (10**precision)) and doc.is_internal_transfer():
				warehouse_asset_account = ""
				if doc.get("is_internal_customer"):
					_inv_dict = doc.get_inventory_account_dict(
						item_row, inventory_account_map, warehouse_field="target_warehouse"
					)
					warehouse_asset_account = _inv_dict.get("account") if _inv_dict else None
				elif doc.get("is_internal_supplier"):
					_inv_dict = doc.get_inventory_account_dict(item_row, inventory_account_map)
					warehouse_asset_account = _inv_dict.get("account") if _inv_dict else None

				expense_account = frappe.get_cached_value("Company", doc.company, "default_expense_account")
				if not expense_account:
					frappe.throw(
						_(
							"Please set default cost of goods sold account in company {0} for booking rounding gain and loss during stock transfer"
						).format(frappe.bold(doc.company))
					)

				gl_list.append(
					self.get_gl_dict(
						{
							"account": expense_account,
							"against": warehouse_asset_account,
							"cost_center": item_row.cost_center,
							"project": item_row.project or doc.get("project"),
							"remarks": _("Rounding gain/loss Entry for Stock Transfer"),
							"debit": sle_rounding_diff,
							"is_opening": item_row.get("is_opening") or doc.get("is_opening") or "No",
						},
						_inv_dict["account_currency"],
						item=item_row,
					)
				)

				gl_list.append(
					self.get_gl_dict(
						{
							"account": warehouse_asset_account,
							"against": expense_account,
							"cost_center": item_row.cost_center,
							"remarks": _("Rounding gain/loss Entry for Stock Transfer"),
							"credit": sle_rounding_diff,
							"project": item_row.get("project") or doc.get("project"),
							"is_opening": item_row.get("is_opening") or doc.get("is_opening") or "No",
						},
						item=item_row,
					)
				)

		if warehouse_with_no_account:
			for wh in warehouse_with_no_account:
				if frappe.get_cached_value("Warehouse", wh, "company"):
					frappe.throw(
						_(
							"Warehouse {0} is not linked to any account, please mention the account in the warehouse record or set default inventory account in company {1}."
						).format(wh, doc.company)
					)

		if self.book_expenses_added_to_stock:
			self.append_expenses_added_to_stock_entries(gl_list, voucher_details, sle_map)

		return process_gl_map(
			gl_list, precision=precision, from_repost=frappe.flags.through_repost_item_valuation
		)

	def get_debit_field_precision(self):
		if not frappe.flags.debit_field_precision:
			frappe.flags.debit_field_precision = frappe.get_precision("GL Entry", "debit_in_account_currency")

		return frappe.flags.debit_field_precision

	def book_stock_expense_enabled(self):
		if not hasattr(self, "_book_stock_expense_enabled"):
			self._book_stock_expense_enabled = cint(
				frappe.db.get_single_value("Accounts Settings", "book_stock_expense_gl_entries")
			)

		return self._book_stock_expense_enabled

	def append_expenses_added_to_stock_entries(self, gl_list, voucher_details, sle_map):
		if not self.book_stock_expense_enabled():
			return

		precision = self.get_debit_field_precision()

		for item_row in voucher_details:
			sle_list = sle_map.get(item_row.name)
			if not sle_list:
				continue

			amount = flt(sum(flt(sle.stock_value_difference) for sle in sle_list), precision)
			if not amount:
				continue

			item_code = item_row.get("item_code") or sle_list[0].item_code
			self.append_expenses_added_to_stock_pair(gl_list, item_code, amount, item_row)

	def append_expenses_added_to_stock_pair(self, gl_list, item_code, amount, item_row):
		doc = self.doc
		fields = ("expenses_added_to_stock_account", "expenses_added_to_stock_contra_account")
		details = get_expenses_added_to_stock_accounts(item_code, doc.company)

		if not any(details.get(field) for field in fields):
			return

		for field in fields:
			if not details.get(field):
				frappe.throw(
					_("Please set {0} in Company {1} or in the Item Defaults of Item {2}").format(
						frappe.bold(_(frappe.unscrub(field))), doc.company, item_code
					)
				)

		cost_center = item_row.get("cost_center") or frappe.get_cached_value(
			"Company", doc.company, "cost_center"
		)
		remarks = _("Expenses Added To Stock for Item {0}").format(item_code)
		common_args = {
			"cost_center": cost_center,
			"project": item_row.get("project") or doc.get("project"),
			"remarks": remarks,
		}

		gl_list.append(
			self.get_gl_dict(
				{
					"account": details.expenses_added_to_stock_account,
					"against": details.expenses_added_to_stock_contra_account,
					"debit": amount,
					**common_args,
				},
				item=item_row,
			)
		)
		gl_list.append(
			self.get_gl_dict(
				{
					"account": details.expenses_added_to_stock_contra_account,
					"against": details.expenses_added_to_stock_account,
					"debit": -1 * amount,
					**common_args,
				},
				item=item_row,
			)
		)

	def get_voucher_details(self, default_expense_account, default_cost_center, sle_map):
		details = self.doc.get("items")

		if default_expense_account or default_cost_center:
			for d in details:
				if default_expense_account and not d.get("expense_account"):
					d.expense_account = default_expense_account
				if default_cost_center and not d.get("cost_center"):
					d.cost_center = default_cost_center

		return details

	def check_expense_account(self, item):
		if not item.get("expense_account"):
			msg = _("Please set an Expense Account in the Items table")
			frappe.throw(
				_("Row #{0}: Expense Account not set for the Item {1}. {2}").format(
					item.idx, frappe.bold(item.item_code), msg
				),
				title=_("Expense Account Missing"),
			)

		else:
			is_expense_account = (
				frappe.get_cached_value("Account", item.get("expense_account"), "report_type")
				== "Profit and Loss"
			)
			if self.enforce_pl_expense_account and not is_expense_account:
				frappe.throw(
					_("Expense / Difference account ({0}) must be a 'Profit or Loss' account").format(
						item.get("expense_account")
					)
				)
			if is_expense_account and not item.get("cost_center"):
				frappe.throw(
					_("{0} {1}: Cost Center is mandatory for Item {2}").format(
						_(self.doc.doctype), self.doc.name, item.get("item_code")
					)
				)


@frappe.request_cache
def get_expenses_added_to_stock_accounts(item_code, company):
	from erpnext.stock.doctype.item.item import get_item_defaults

	fields = ["expenses_added_to_stock_account", "expenses_added_to_stock_contra_account"]
	defaults = get_item_defaults(item_code, company)

	details = frappe._dict({field: defaults.get(field) for field in fields})

	if not details.expenses_added_to_stock_account:
		details = frappe.db.get_value(
			"Item Default", {"parent": defaults.item_group, "company": company}, fields, as_dict=1
		) or frappe._dict({})

	if not details.expenses_added_to_stock_account and defaults.get("brand"):
		details = frappe.db.get_value(
			"Item Default", {"parent": defaults.brand, "company": company}, fields, as_dict=1
		) or frappe._dict({})

	for field in fields:
		if not details.get(field):
			details[field] = frappe.get_cached_value("Company", company, field)

	return details
