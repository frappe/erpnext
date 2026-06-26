# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.general_ledger import process_gl_map
from erpnext.accounts.services.base_gl_composer import BaseGLComposer


class BaseStockGLComposer(BaseGLComposer):
	"""Shared GL composition logic for stock vouchers.

	Subclasses override ``compose()`` and call ``super().compose()`` to get the
	warehouse ↔ expense-account GL pairs, then append any doctype-specific
	entries on top.
	"""

	def compose(
		self,
		inventory_account_map: dict | None = None,
		default_expense_account: str | None = None,
		default_cost_center: str | None = None,
	) -> list:
		doc = self.doc

		if not inventory_account_map:
			inventory_account_map = doc.get_inventory_account_map()

		sle_map = doc.get_stock_ledger_details()
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

		return process_gl_map(
			gl_list, precision=precision, from_repost=frappe.flags.through_repost_item_valuation
		)

	def get_debit_field_precision(self):
		if not frappe.flags.debit_field_precision:
			frappe.flags.debit_field_precision = frappe.get_precision("GL Entry", "debit_in_account_currency")

		return frappe.flags.debit_field_precision

	def get_voucher_details(self, default_expense_account, default_cost_center, sle_map):
		doc = self.doc
		if doc.doctype == "Stock Reconciliation":
			reconciliation_purpose = frappe.db.get_value(doc.doctype, doc.name, "purpose")
			is_opening = "Yes" if reconciliation_purpose == "Opening Stock" else "No"
			details = []
			for voucher_detail_no in sle_map:
				details.append(
					frappe._dict(
						{
							"name": voucher_detail_no,
							"expense_account": default_expense_account,
							"cost_center": default_cost_center,
							"is_opening": is_opening,
						}
					)
				)
			return details
		else:
			details = doc.get("items")

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
			if (
				self.doc.doctype
				not in (
					"Purchase Receipt",
					"Purchase Invoice",
					"Stock Reconciliation",
					"Stock Entry",
					"Subcontracting Receipt",
					"Delivery Note",
				)
				and not is_expense_account
			):
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
