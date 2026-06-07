# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.general_ledger import process_gl_map
from erpnext.accounts.utils import get_account_currency
from erpnext.stock.services.base_stock_gl_composer import BaseStockGLComposer


class SubcontractingReceiptGLComposer(BaseStockGLComposer):
	"""GL composer for Subcontracting Receipt.

	Builds GL entries for accepted stock, service cost, supplier warehouse
	(raw materials), additional costs, LCV, and divisional loss.
	"""

	def compose(self, inventory_account_map: dict | None = None) -> list:
		import erpnext

		doc = self.doc
		if not erpnext.is_perpetual_inventory_enabled(doc.company):
			return []

		gl_entries = []
		self._make_item_gl_entries(gl_entries, inventory_account_map)
		self._make_item_gl_entries_for_lcv(gl_entries, inventory_account_map)

		return process_gl_map(gl_entries, from_repost=frappe.flags.through_repost_item_valuation)

	def _make_item_gl_entries(self, gl_entries: list, inventory_account_map: dict | None) -> None:
		doc = self.doc
		warehouse_with_no_account = []

		supplied_items_details = frappe._dict()
		for item in doc.supplied_items:
			supplied_items_details.setdefault(item.reference_name, []).append(
				frappe._dict(
					{
						"item_code": item.rm_item_code,
						"amount": item.amount,
						"expense_account": item.expense_account,
						"cost_center": item.cost_center,
					}
				)
			)

		for item in doc.items:
			if flt(item.rate) and flt(item.qty):
				_inv_dict = doc.get_inventory_account_dict(item, inventory_account_map)

				if _inv_dict.get("account"):
					stock_value_diff = frappe.db.get_value(
						"Stock Ledger Entry",
						{
							"voucher_type": "Subcontracting Receipt",
							"voucher_no": doc.name,
							"voucher_detail_no": item.name,
							"warehouse": item.warehouse,
							"is_cancelled": 0,
						},
						"stock_value_difference",
					)

					remarks = doc.get("remarks") or _("Accounting Entry for Stock")

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=_inv_dict["account"],
						cost_center=item.cost_center,
						debit=stock_value_diff,
						credit=0.0,
						remarks=remarks,
						against_account=item.expense_account,
						account_currency=_inv_dict["account_currency"],
						project=item.project,
						item=item,
					)

					service_cost = flt(
						item.service_cost_per_qty, item.precision("service_cost_per_qty")
					) * flt(item.qty, item.precision("qty"))

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=item.expense_account,
						cost_center=item.cost_center,
						debit=0.0,
						credit=flt(stock_value_diff) - service_cost,
						remarks=remarks,
						against_account=_inv_dict["account"],
						account_currency=get_account_currency(item.expense_account),
						project=item.project,
						item=item,
					)

					service_account = item.service_expense_account or item.expense_account
					self.add_gl_entry(
						gl_entries=gl_entries,
						account=service_account,
						cost_center=item.cost_center,
						debit=0.0,
						credit=service_cost,
						remarks=remarks,
						against_account=_inv_dict["account"],
						account_currency=get_account_currency(service_account),
						project=item.project,
						item=item,
					)

					if flt(item.rm_supp_cost):
						for rm_item in supplied_items_details.get(item.name):
							_inv_dict = doc.get_inventory_account_dict(
								rm_item, inventory_account_map, "supplier_warehouse"
							)

							self.add_gl_entry(
								gl_entries=gl_entries,
								account=_inv_dict.get("account"),
								cost_center=rm_item.cost_center or item.cost_center,
								debit=0.0,
								credit=flt(rm_item.amount),
								remarks=remarks,
								against_account=rm_item.expense_account or item.expense_account,
								account_currency=_inv_dict.get("account_currency"),
								project=item.project,
								item=item,
							)
							self.add_gl_entry(
								gl_entries=gl_entries,
								account=rm_item.expense_account or item.expense_account,
								cost_center=rm_item.cost_center or item.cost_center,
								debit=flt(rm_item.amount),
								credit=0.0,
								remarks=remarks,
								against_account=_inv_dict.get("account"),
								account_currency=get_account_currency(item.expense_account),
								project=item.project,
								item=item,
							)

					if item.additional_cost_per_qty:
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=item.expense_account,
							cost_center=doc.cost_center or doc.get_company_default("cost_center"),
							debit=item.qty * item.additional_cost_per_qty,
							credit=0.0,
							remarks=remarks,
							against_account=None,
							account_currency=get_account_currency(item.expense_account),
						)

					if divisional_loss := flt(item.amount - stock_value_diff, item.precision("amount")):
						loss_account = doc.get_company_default(
							"stock_adjustment_account", ignore_validation=True
						)

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=loss_account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=divisional_loss,
							remarks=remarks,
							against_account=item.expense_account,
							account_currency=get_account_currency(loss_account),
							project=item.project,
							item=item,
						)
						self.add_gl_entry(
							gl_entries=gl_entries,
							account=item.expense_account,
							cost_center=item.cost_center,
							debit=divisional_loss,
							credit=0.0,
							remarks=remarks,
							against_account=loss_account,
							account_currency=get_account_currency(item.expense_account),
							project=item.project,
							item=item,
						)
				elif (
					item.warehouse not in warehouse_with_no_account
					or item.rejected_warehouse not in warehouse_with_no_account
				):
					warehouse_with_no_account.append(item.warehouse)

		for row in doc.additional_costs:
			credit_amount = (
				flt(row.base_amount)
				if (row.base_amount or row.account_currency != doc.company_currency)
				else flt(row.amount)
			)

			self.add_gl_entry(
				gl_entries=gl_entries,
				account=row.expense_account,
				cost_center=doc.cost_center or doc.get_company_default("cost_center"),
				debit=0.0,
				credit=credit_amount,
				remarks=remarks,
				against_account=None,
				account_currency=get_account_currency(row.expense_account),
			)

		if warehouse_with_no_account:
			frappe.msgprint(
				_("No accounting entries for the following warehouses")
				+ ": \n"
				+ "\n".join(warehouse_with_no_account)
			)

	def _make_item_gl_entries_for_lcv(self, gl_entries: list, inventory_account_map: dict | None) -> None:
		doc = self.doc
		landed_cost_entries = doc.get_item_account_wise_lcv_entries()

		if not landed_cost_entries:
			return

		for item in doc.items:
			if item.landed_cost_voucher_amount and landed_cost_entries:
				remarks = _("Accounting Entry for Landed Cost Voucher for SCR {0}").format(doc.name)
				if (item.item_code, item.name) in landed_cost_entries:
					_inv_dict = doc.get_inventory_account_dict(item, inventory_account_map)

					for account, amount in landed_cost_entries[(item.item_code, item.name)].items():
						account_currency = get_account_currency(account)
						credit_amount = (
							flt(amount["base_amount"])
							if (amount["base_amount"] or account_currency != doc.company_currency)
							else flt(amount["amount"])
						)

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=credit_amount,
							remarks=remarks,
							against_account=_inv_dict["account"],
							credit_in_account_currency=flt(amount["amount"]),
							account_currency=account_currency,
							project=item.project,
							item=item,
						)

						account_currency = get_account_currency(item.expense_account)

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=item.expense_account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=credit_amount * -1,
							remarks=remarks,
							against_account=_inv_dict["account"],
							debit_in_account_currency=flt(amount["amount"]),
							account_currency=account_currency,
							project=item.project,
							item=item,
						)
