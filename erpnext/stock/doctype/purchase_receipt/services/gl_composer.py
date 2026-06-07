# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

import erpnext
from erpnext.accounts.general_ledger import process_gl_map
from erpnext.accounts.utils import get_account_currency
from erpnext.stock.services.base_stock_gl_composer import BaseStockGLComposer


class PurchaseReceiptGLComposer(BaseStockGLComposer):
	"""GL composer for Purchase Receipt.

	Builds GL entries for stock/asset inward, taxes, purchase expense, and
	regional adjustments. Does not delegate to the base stock GL loop —
	PR has its own per-item logic (provisional accounting, fixed assets, LCV,
	sub-contracting, divisional loss).
	"""

	def compose(
		self,
		inventory_account_map: dict | None = None,
		via_landed_cost_voucher: bool = False,
	) -> list:
		gl_entries = []
		self._make_item_gl_entries(gl_entries, inventory_account_map)
		self._make_tax_gl_entries(gl_entries, via_landed_cost_voucher)
		self.doc.set_gl_entry_for_purchase_expense(gl_entries)

		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import update_regional_gl_entries

		update_regional_gl_entries(gl_entries, self.doc)

		return process_gl_map(gl_entries, from_repost=frappe.flags.through_repost_item_valuation)

	def _make_item_gl_entries(self, gl_entries: list, inventory_account_map: dict | None) -> None:
		from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import (
			get_purchase_document_details,
		)
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import get_stock_value_difference

		doc = self.doc
		provisional_accounting_for_non_stock_items = cint(
			frappe.db.get_value("Company", doc.company, "enable_provisional_accounting_for_non_stock_items")
		)

		exchange_rate_map, net_rate_map = get_purchase_document_details(doc)
		stock_items = doc.get_stock_items()
		warehouse_with_no_account = []

		def validate_account(account_type):
			frappe.throw(_("{0} account not found while submitting purchase receipt").format(account_type))

		def make_item_asset_inward_gl_entry(item, stock_value_diff, stock_asset_account_name):
			account_currency = get_account_currency(stock_asset_account_name)
			if not stock_asset_account_name:
				validate_account("Asset or warehouse account")
			self.add_gl_entry(
				gl_entries=gl_entries,
				account=stock_asset_account_name,
				cost_center=d.cost_center,
				debit=stock_value_diff,
				credit=0.0,
				remarks=remarks,
				against_account=stock_asset_rbnb,
				account_currency=account_currency,
				item=item,
			)

		def make_stock_received_but_not_billed_entry(item):
			if (
				doc.get("is_return")
				and item.return_qty_from_rejected_warehouse
				and not frappe.db.get_single_value(
					"Buying Settings", "set_valuation_rate_for_rejected_materials"
				)
			):
				return 0.0

			account = stock_asset_rbnb
			if item.from_warehouse:
				_inv_dict = doc.get_inventory_account_dict(item, inventory_account_map, "from_warehouse")
				account = _inv_dict["account"]

			account_currency = get_account_currency(account)

			credit_amount = (
				flt(item.base_net_amount, item.precision("base_net_amount"))
				if account_currency == doc.company_currency
				else flt(item.net_amount, item.precision("net_amount"))
			)

			outgoing_amount = item.base_net_amount
			if doc.is_internal_transfer() and item.valuation_rate:
				outgoing_amount = abs(get_stock_value_difference(doc.name, item.name, item.from_warehouse))
				credit_amount = outgoing_amount

			if item.get("rejected_qty") and frappe.db.get_single_value(
				"Buying Settings", "set_valuation_rate_for_rejected_materials"
			):
				outgoing_amount += get_stock_value_difference(doc.name, item.name, item.rejected_warehouse)
				credit_amount = outgoing_amount

			if credit_amount:
				if not account:
					validate_account("Stock or Asset Received But Not Billed")

				self.add_gl_entry(
					gl_entries=gl_entries,
					account=account,
					cost_center=item.cost_center,
					debit=-1 * flt(outgoing_amount, item.precision("base_net_amount")),
					credit=0.0,
					remarks=remarks,
					against_account=stock_asset_account_name,
					debit_in_account_currency=-1 * flt(outgoing_amount, item.precision("base_net_amount")),
					account_currency=account_currency,
					item=item,
				)

				if d.get("purchase_invoice"):
					if (
						exchange_rate_map[item.purchase_invoice]
						and doc.conversion_rate != exchange_rate_map[item.purchase_invoice]
						and item.net_rate == net_rate_map[item.purchase_invoice_item]
					):
						discrepancy_caused_by_exchange_rate_difference = (item.qty * item.net_rate) * (
							exchange_rate_map[item.purchase_invoice] - doc.conversion_rate
						)

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=discrepancy_caused_by_exchange_rate_difference,
							remarks=remarks,
							against_account=doc.supplier,
							debit_in_account_currency=-1 * discrepancy_caused_by_exchange_rate_difference,
							account_currency=account_currency,
							item=item,
						)

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=doc.get_company_default("exchange_gain_loss_account"),
							cost_center=d.cost_center,
							debit=discrepancy_caused_by_exchange_rate_difference,
							credit=0.0,
							remarks=remarks,
							against_account=doc.supplier,
							debit_in_account_currency=-1 * discrepancy_caused_by_exchange_rate_difference,
							account_currency=account_currency,
							item=item,
						)

			return outgoing_amount

		def make_landed_cost_gl_entries(item):
			if item.landed_cost_voucher_amount and landed_cost_entries:
				if (item.item_code, item.name) in landed_cost_entries:
					for account, amount in landed_cost_entries[(item.item_code, item.name)].items():
						account_currency = get_account_currency(account)
						credit_amount = (
							flt(amount["base_amount"])
							if (amount["base_amount"] or account_currency != doc.company_currency)
							else flt(amount["amount"])
						)

						if not account:
							validate_account("Landed Cost Account")

						self.add_gl_entry(
							gl_entries=gl_entries,
							account=account,
							cost_center=item.cost_center,
							debit=0.0,
							credit=credit_amount,
							remarks=remarks,
							against_account=stock_asset_account_name,
							credit_in_account_currency=flt(amount["amount"]),
							account_currency=account_currency,
							project=item.project,
							item=item,
						)

		def make_amount_difference_entry(item):
			if item.amount_difference_with_purchase_invoice and stock_asset_rbnb:
				account_currency = get_account_currency(stock_asset_rbnb)
				self.add_gl_entry(
					gl_entries=gl_entries,
					account=stock_asset_rbnb,
					cost_center=item.cost_center,
					debit=0.0,
					credit=flt(item.amount_difference_with_purchase_invoice),
					remarks=_("Adjustment based on Purchase Invoice rate"),
					against_account=stock_asset_account_name,
					account_currency=account_currency,
					project=item.project,
					item=item,
				)

		def make_sub_contracting_gl_entries(item):
			if flt(item.rm_supp_cost) and supplier_warehouse_account:
				self.add_gl_entry(
					gl_entries=gl_entries,
					account=supplier_warehouse_account,
					cost_center=item.cost_center,
					debit=0.0,
					credit=flt(item.rm_supp_cost),
					remarks=remarks,
					against_account=stock_asset_account_name,
					account_currency=supplier_warehouse_account_currency,
					item=item,
				)

		def make_divisional_loss_gl_entry(item, outgoing_amount):
			if item.is_fixed_asset:
				return

			valuation_amount_as_per_doc = (
				flt(outgoing_amount, d.precision("base_net_amount"))
				+ flt(item.landed_cost_voucher_amount)
				+ flt(item.rm_supp_cost)
				+ flt(item.item_tax_amount)
				+ flt(item.amount_difference_with_purchase_invoice)
			)

			divisional_loss = flt(
				valuation_amount_as_per_doc - flt(stock_value_diff), item.precision("base_net_amount")
			)

			if item.get("rejected_qty") and frappe.db.get_single_value(
				"Buying Settings", "set_valuation_rate_for_rejected_materials"
			):
				rejected_item_cost = get_stock_value_difference(doc.name, item.name, item.rejected_warehouse)
				divisional_loss -= rejected_item_cost

			if divisional_loss:
				loss_account = (
					doc.get_company_default("default_expense_account", ignore_validation=True)
					or stock_asset_rbnb
				)

				if doc.is_return and item.expense_account:
					loss_account = item.expense_account

				cost_center = item.cost_center or frappe.get_cached_value(
					"Company", doc.company, "cost_center"
				)
				account_currency = get_account_currency(loss_account)
				self.add_gl_entry(
					gl_entries=gl_entries,
					account=loss_account,
					cost_center=cost_center,
					debit=divisional_loss,
					credit=0.0,
					remarks=remarks,
					against_account=stock_asset_account_name,
					account_currency=account_currency,
					project=item.project,
					item=item,
				)

		for d in doc.get("items"):
			remarks = doc.get("remarks") or _("Accounting Entry for {0}").format(
				"Asset" if d.is_fixed_asset else "Stock"
			)

			if (
				provisional_accounting_for_non_stock_items
				and d.item_code not in stock_items
				and flt(d.qty)
				and d.get("provisional_expense_account")
				and not d.is_fixed_asset
			):
				doc.add_provisional_gl_entry(
					d, gl_entries, doc.posting_date, d.get("provisional_expense_account")
				)
			elif flt(d.qty) and (flt(d.valuation_rate) or doc.is_return):
				if not (
					(erpnext.is_perpetual_inventory_enabled(doc.company) and d.item_code in stock_items)
					or (d.is_fixed_asset and not d.purchase_invoice)
				):
					continue

				stock_asset_rbnb = (
					doc.get_company_default("asset_received_but_not_billed")
					if d.is_fixed_asset
					else doc.get_company_default("stock_received_but_not_billed")
				)
				landed_cost_entries = doc.get_item_account_wise_lcv_entries()
				if d.is_fixed_asset:
					stock_asset_account_name = d.expense_account
					stock_value_diff = (
						flt(d.base_net_amount) + flt(d.item_tax_amount) + flt(d.landed_cost_voucher_amount)
					)
				elif inventory_account := doc.get_inventory_account_dict(d, inventory_account_map):
					stock_value_diff = get_stock_value_difference(doc.name, d.name, d.warehouse)
					stock_asset_account_name = inventory_account["account"]

					supplier_warehouse_account = None
					supplier_warehouse_account_currency = None
					if doc.supplier_warehouse:
						if _inv_dict := doc.get_inventory_account_dict(
							d, inventory_account_map, "supplier_warehouse"
						):
							supplier_warehouse_account = _inv_dict["account"]
							supplier_warehouse_account_currency = _inv_dict["account_currency"]

					if (
						flt(stock_value_diff) == flt(d.rm_supp_cost)
						and supplier_warehouse_account
						and stock_asset_account_name == supplier_warehouse_account
					):
						continue

				if (flt(d.valuation_rate) or doc.is_return or d.is_fixed_asset) and flt(d.qty):
					make_item_asset_inward_gl_entry(d, stock_value_diff, stock_asset_account_name)
					outgoing_amount = make_stock_received_but_not_billed_entry(d)
					make_landed_cost_gl_entries(d)
					make_amount_difference_entry(d)
					make_sub_contracting_gl_entries(d)
					make_divisional_loss_gl_entry(d, outgoing_amount)
			elif (d.warehouse and d.qty and d.warehouse not in warehouse_with_no_account) or (
				not frappe.db.get_single_value("Buying Settings", "set_valuation_rate_for_rejected_materials")
				and d.rejected_warehouse
				and d.rejected_warehouse not in warehouse_with_no_account
			):
				warehouse_with_no_account.append(d.warehouse or d.rejected_warehouse)

			if d.is_fixed_asset and d.landed_cost_voucher_amount:
				doc.update_assets(d, d.valuation_rate)

			if d.rejected_qty and frappe.db.get_single_value(
				"Buying Settings", "set_valuation_rate_for_rejected_materials"
			):
				stock_asset_rbnb = (
					doc.get_company_default("asset_received_but_not_billed")
					if d.is_fixed_asset
					else doc.get_company_default("stock_received_but_not_billed")
				)

				stock_value_diff = get_stock_value_difference(doc.name, d.name, d.rejected_warehouse)
				_inv_dict = doc.get_inventory_account_dict(d, inventory_account_map, "rejected_warehouse")
				stock_asset_account_name = _inv_dict["account"]

				make_item_asset_inward_gl_entry(d, stock_value_diff, stock_asset_account_name)
				if not d.qty:
					make_stock_received_but_not_billed_entry(d)

		if warehouse_with_no_account:
			frappe.msgprint(
				_("No accounting entries for the following warehouses")
				+ ": \n"
				+ "\n".join(warehouse_with_no_account)
			)

	def _make_tax_gl_entries(self, gl_entries: list, via_landed_cost_voucher: bool = False) -> None:
		doc = self.doc
		negative_expense_to_be_booked = sum([flt(d.item_tax_amount) for d in doc.get("items")])
		valuation_tax = {}
		for tax in doc.get("taxes"):
			if tax.category in ("Valuation", "Valuation and Total") and flt(
				tax.base_tax_amount_after_discount_amount
			):
				if not tax.cost_center:
					frappe.throw(
						_("Cost Center is required in row {0} in Taxes table for type {1}").format(
							tax.idx, _(tax.category)
						)
					)
				valuation_tax.setdefault(tax.name, 0)
				valuation_tax[tax.name] += (tax.add_deduct_tax == "Add" and 1 or -1) * flt(
					tax.base_tax_amount_after_discount_amount
				)

		if negative_expense_to_be_booked and valuation_tax:
			against_accounts = ", ".join([d.account for d in gl_entries if flt(d.debit) > 0])
			total_valuation_amount = sum(valuation_tax.values())
			amount_including_divisional_loss = negative_expense_to_be_booked
			i = 1
			for tax in doc.get("taxes"):
				if valuation_tax.get(tax.name):
					account = tax.account_head
					if i == len(valuation_tax):
						applicable_amount = amount_including_divisional_loss
					else:
						applicable_amount = negative_expense_to_be_booked * (
							valuation_tax[tax.name] / total_valuation_amount
						)
						amount_including_divisional_loss -= applicable_amount

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=account,
						cost_center=tax.cost_center,
						debit=0.0,
						credit=applicable_amount,
						remarks=doc.remarks or _("Accounting Entry for Stock"),
						against_account=against_accounts,
						item=tax,
					)

					i += 1
