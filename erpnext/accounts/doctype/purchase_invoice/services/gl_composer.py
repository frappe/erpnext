# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, get_link_to_form

import erpnext
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center
from erpnext.accounts.services.base_gl_composer import BaseGLComposer
from erpnext.accounts.services.taxes import TaxService
from erpnext.accounts.utils import get_account_currency


class PurchaseInvoiceGLComposer(BaseGLComposer):
	"""Assembles the GL entries for a Purchase Invoice."""

	def compose(self, inventory_account_map=None):
		from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_regional_gl_entries
		from erpnext.accounts.general_ledger import merge_similar_entries

		doc = self.doc
		doc.auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(doc.company)

		if doc.auto_accounting_for_stock:
			doc.stock_received_but_not_billed = doc.get_company_default("stock_received_but_not_billed")
		else:
			doc.stock_received_but_not_billed = None

		doc.negative_expense_to_be_booked = 0.0
		gl_entries = []

		self.make_supplier_gl_entry(gl_entries)
		self.make_item_gl_entries(gl_entries)
		self.make_precision_loss_gl_entry(gl_entries)

		self.make_tax_gl_entries(gl_entries)
		self.make_internal_transfer_gl_entries(gl_entries)
		self.make_gl_entries_for_tax_withholding(gl_entries)

		gl_entries = make_regional_gl_entries(gl_entries, doc)
		gl_entries = merge_similar_entries(gl_entries)

		self.make_payment_gl_entries(gl_entries)
		self.make_write_off_gl_entry(gl_entries)
		self.make_gle_for_rounding_adjustment(gl_entries)
		doc.set_transaction_currency_and_rate_in_gl_map(gl_entries)
		doc.set_gl_entry_for_purchase_expense(gl_entries)
		return gl_entries

	def make_precision_loss_gl_entry(self, gl_entries):
		doc = self.doc
		(
			round_off_account,
			round_off_cost_center,
			_round_off_for_opening,
		) = get_round_off_account_and_cost_center(
			doc.company, "Purchase Invoice", doc.name, doc.use_company_roundoff_cost_center
		)

		precision_loss = doc.get("base_net_total") - flt(
			doc.get("net_total") * doc.conversion_rate, doc.precision("net_total")
		)

		if precision_loss:
			gl_entries.append(
				doc.get_gl_dict(
					{
						"account": round_off_account,
						"against": doc.supplier,
						"credit": precision_loss,
						"cost_center": round_off_cost_center
						if doc.use_company_roundoff_cost_center
						else doc.cost_center or round_off_cost_center,
						"remarks": _("Net total calculation precision loss"),
					}
				)
			)

	def make_supplier_gl_entry(self, gl_entries):
		doc = self.doc
		grand_total = (
			doc.rounded_total if (doc.rounding_adjustment and doc.rounded_total) else doc.grand_total
		)
		base_grand_total = flt(
			doc.base_rounded_total
			if (doc.base_rounding_adjustment and doc.base_rounded_total)
			else doc.base_grand_total,
			doc.precision("base_grand_total"),
		)
		if grand_total and not doc.is_internal_transfer():
			self.add_supplier_gl_entry(gl_entries, base_grand_total, grand_total)

	def add_supplier_gl_entry(
		self,
		gl_entries,
		base_grand_total,
		grand_total,
		against_account=None,
		remarks=None,
		skip_merge=False,
	):
		doc = self.doc
		against_voucher = doc.name
		if doc.is_return and doc.return_against and not doc.update_outstanding_for_self:
			against_voucher = doc.return_against

		gl = {
			"account": doc.credit_to,
			"party_type": "Supplier",
			"party": doc.supplier,
			"due_date": doc.due_date,
			"against": against_account or doc.against_expense_account,
			"credit": base_grand_total,
			"credit_in_account_currency": base_grand_total
			if doc.party_account_currency == doc.company_currency
			else grand_total,
			"credit_in_transaction_currency": grand_total,
			"against_voucher": against_voucher,
			"against_voucher_type": doc.doctype,
			"project": doc.project,
			"cost_center": doc.cost_center,
			"_skip_merge": skip_merge,
		}
		if remarks:
			gl["remarks"] = remarks
		gl_entries.append(self.get_gl_dict(gl, doc.party_account_currency, item=doc))

	def make_item_gl_entries(self, gl_entries):
		from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import (
			get_purchase_document_details,
		)

		doc = self.doc
		tax_service = TaxService(doc)
		stock_items = doc.get_stock_items()
		if doc.update_stock and doc.auto_accounting_for_stock:
			inventory_account_map = doc.get_inventory_account_map()

		landed_cost_entries = doc.get_item_account_wise_lcv_entries()

		voucher_wise_stock_value = {}
		if doc.update_stock:
			stock_ledger_entries = frappe.get_all(
				"Stock Ledger Entry",
				fields=["voucher_detail_no", "stock_value_difference", "warehouse"],
				filters={"voucher_no": doc.name, "voucher_type": doc.doctype, "is_cancelled": 0},
			)
			for d in stock_ledger_entries:
				voucher_wise_stock_value.setdefault(
					(d.voucher_detail_no, d.warehouse), d.stock_value_difference
				)

		valuation_tax_accounts = [
			d.account_head
			for d in doc.get("taxes")
			if d.category in ("Valuation", "Valuation and Total")
			and flt(d.base_tax_amount_after_discount_amount)
		]

		exchange_rate_map, net_rate_map = get_purchase_document_details(doc)

		provisional_accounting_for_non_stock_items = cint(
			frappe.get_cached_value(
				"Company", doc.company, "enable_provisional_accounting_for_non_stock_items"
			)
		)
		if provisional_accounting_for_non_stock_items:
			self.get_provisional_accounts()

		adjust_incoming_rate = frappe.db.get_single_value(
			"Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate"
		)

		for item in doc.get("items"):
			if flt(item.base_net_amount) or (doc.get("update_stock") and item.valuation_rate):
				if item.item_code:
					frappe.get_cached_value("Item", item.item_code, "asset_category")

				if (
					doc.update_stock
					and doc.auto_accounting_for_stock
					and (item.item_code in stock_items or item.is_fixed_asset)
				):
					account_currency = get_account_currency(item.expense_account)
					warehouse_debit_amount = self.make_stock_adjustment_entry(
						gl_entries, item, voucher_wise_stock_value, account_currency
					)

					if item.from_warehouse:
						_inv_dict = doc.get_inventory_account_dict(item, inventory_account_map)
						_inv_dict_from_warehouse = doc.get_inventory_account_dict(
							item, inventory_account_map, "from_warehouse"
						)

						gl_entries.append(
							self.get_gl_dict(
								{
									"account": _inv_dict["account"],
									"against": _inv_dict_from_warehouse["account"],
									"cost_center": item.cost_center,
									"project": item.project or doc.project,
									"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
									"debit": warehouse_debit_amount,
									"debit_in_transaction_currency": item.net_amount,
								},
								_inv_dict["account_currency"],
								item=item,
							)
						)

						credit_amount = item.base_net_amount
						if doc.is_internal_supplier and item.valuation_rate:
							credit_amount = flt(item.valuation_rate * item.stock_qty)

						# Intentionally passed negative debit amount to avoid incorrect GL Entry validation
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": _inv_dict_from_warehouse["account"],
									"against": _inv_dict["account"],
									"cost_center": item.cost_center,
									"project": item.project or doc.project,
									"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
									"debit": -1 * flt(credit_amount, item.precision("base_net_amount")),
									"debit_in_transaction_currency": item.net_amount,
								},
								_inv_dict_from_warehouse["account_currency"],
								item=item,
							)
						)

						if not doc.is_internal_transfer():
							gl_entries.append(
								self.get_gl_dict(
									{
										"account": item.expense_account,
										"against": doc.supplier,
										"debit": flt(item.base_net_amount, item.precision("base_net_amount")),
										"debit_in_transaction_currency": item.net_amount,
										"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
										"cost_center": item.cost_center,
										"project": item.project,
									},
									account_currency,
									item=item,
								)
							)

					else:
						if not doc.is_internal_transfer():
							gl_entries.append(
								self.get_gl_dict(
									{
										"account": item.expense_account,
										"against": doc.supplier,
										"debit": warehouse_debit_amount,
										"debit_in_transaction_currency": flt(
											warehouse_debit_amount / doc.conversion_rate,
											item.precision("net_amount"),
										),
										"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
										"cost_center": item.cost_center,
										"project": item.project or doc.project,
									},
									account_currency,
									item=item,
								)
							)

					# Amount added through landed-cost-voucher
					if landed_cost_entries:
						if (item.item_code, item.name) in landed_cost_entries:
							for account, base_amount in landed_cost_entries[
								(item.item_code, item.name)
							].items():
								gl_entries.append(
									self.get_gl_dict(
										{
											"account": account,
											"against": item.expense_account,
											"cost_center": item.cost_center,
											"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
											"credit": flt(base_amount["base_amount"]),
											"credit_in_account_currency": flt(base_amount["amount"]),
											"credit_in_transaction_currency": item.net_amount,
											"project": item.project or doc.project,
										},
										item=item,
									)
								)

					# sub-contracting warehouse
					if flt(item.rm_supp_cost):
						supplier_wh_dict = doc.get_inventory_account_dict(
							item, inventory_account_map, "supplier_warehouse"
						)
						supplier_inventory_account = supplier_wh_dict["account"]
						if not supplier_inventory_account:
							frappe.throw(
								_("Please set account in Warehouse {0}").format(doc.supplier_warehouse)
							)
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": supplier_inventory_account,
									"against": item.expense_account,
									"cost_center": item.cost_center,
									"project": item.project or doc.project,
									"remarks": doc.get("remarks") or _("Accounting Entry for Stock"),
									"credit": flt(item.rm_supp_cost),
									"credit_in_transaction_currency": item.net_amount,
								},
								supplier_wh_dict["account_currency"],
								item=item,
							)
						)

				else:
					expense_account = (
						item.expense_account
						if (not item.enable_deferred_expense or doc.is_return)
						else item.deferred_expense_account
					)
					account_currency = get_account_currency(expense_account)
					amount, base_amount = tax_service.get_amount_and_base_amount(item, None)

					if provisional_accounting_for_non_stock_items:
						self.make_provisional_gl_entry(gl_entries, item)

					if not doc.is_internal_transfer():
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": expense_account,
									"against": doc.supplier,
									"debit": base_amount,
									"debit_in_transaction_currency": amount,
									"cost_center": item.cost_center,
									"project": item.project or doc.project,
								},
								account_currency,
								item=item,
							)
						)

						# check if the exchange rate has changed
						if (
							not adjust_incoming_rate
							and item.get("purchase_receipt")
							and doc.auto_accounting_for_stock
						):
							if (
								exchange_rate_map[item.purchase_receipt]
								and doc.conversion_rate != exchange_rate_map[item.purchase_receipt]
								and item.net_rate == net_rate_map[item.pr_detail]
								and item.item_code in stock_items
							):
								discrepancy_caused_by_exchange_rate_difference = (
									item.qty * item.net_rate
								) * (exchange_rate_map[item.purchase_receipt] - doc.conversion_rate)

								gl_entries.append(
									self.get_gl_dict(
										{
											"account": expense_account,
											"against": doc.supplier,
											"debit": discrepancy_caused_by_exchange_rate_difference,
											"cost_center": item.cost_center,
											"project": item.project or doc.project,
										},
										account_currency,
										item=item,
									)
								)
								gl_entries.append(
									self.get_gl_dict(
										{
											"account": doc.get_company_default("exchange_gain_loss_account"),
											"against": doc.supplier,
											"credit": discrepancy_caused_by_exchange_rate_difference,
											"cost_center": item.cost_center,
											"project": item.project or doc.project,
										},
										account_currency,
										item=item,
									)
								)

			if (
				doc.auto_accounting_for_stock
				and doc.is_opening == "No"
				and item.item_code in stock_items
				and item.item_tax_amount
			):
				# Post reverse entry for Stock-Received-But-Not-Billed if booked in Purchase Receipt
				if item.purchase_receipt and valuation_tax_accounts:
					negative_expense_booked_in_pr = frappe.db.sql(
						"""select name from `tabGL Entry`
							where voucher_type='Purchase Receipt' and voucher_no=%s and account in %s""",
						(item.purchase_receipt, valuation_tax_accounts),
					)

					(
						doc.get_company_default("asset_received_but_not_billed")
						if item.is_fixed_asset
						else doc.stock_received_but_not_billed
					)

					if not negative_expense_booked_in_pr:
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": doc.stock_received_but_not_billed,
									"against": doc.supplier,
									"debit": flt(item.item_tax_amount, item.precision("item_tax_amount")),
									"debit_in_transaction_currency": flt(
										item.item_tax_amount / doc.conversion_rate,
										item.precision("item_tax_amount"),
									),
									"remarks": doc.remarks or _("Accounting Entry for Stock"),
									"cost_center": doc.cost_center,
									"project": item.project or doc.project,
								},
								item=item,
							)
						)
						doc.negative_expense_to_be_booked += flt(
							item.item_tax_amount, item.precision("item_tax_amount")
						)

			if item.is_fixed_asset and item.landed_cost_voucher_amount:
				self.update_net_purchase_amount_for_linked_assets(item)

	def get_provisional_accounts(self):
		doc = self.doc
		self.provisional_accounts = frappe._dict()
		linked_purchase_receipts = {d.purchase_receipt for d in doc.items if d.purchase_receipt}
		if not linked_purchase_receipts:
			return

		pr_items = frappe.get_all(
			"Purchase Receipt Item",
			filters={"parent": ("in", linked_purchase_receipts)},
			fields=["name", "provisional_expense_account", "qty", "base_rate", "rate"],
		)
		default_provisional_account = doc.get_company_default("default_provisional_account")
		provisional_accounts = {
			d.provisional_expense_account if d.provisional_expense_account else default_provisional_account
			for d in pr_items
		}

		provisional_gl_entries = frappe.get_all(
			"GL Entry",
			filters={
				"voucher_type": "Purchase Receipt",
				"voucher_no": ("in", linked_purchase_receipts),
				"account": ("in", provisional_accounts),
				"is_cancelled": 0,
			},
			fields=["voucher_detail_no"],
		)
		rows_with_provisional_entries = [d.voucher_detail_no for d in provisional_gl_entries]
		for item in pr_items:
			self.provisional_accounts[item.name] = {
				"provisional_account": item.provisional_expense_account or default_provisional_account,
				"qty": item.qty,
				"base_rate": item.base_rate,
				"rate": item.rate,
				"has_provisional_entry": item.name in rows_with_provisional_entries,
			}

	def make_provisional_gl_entry(self, gl_entries, item):
		if item.purchase_receipt:
			pr_item = self.provisional_accounts.get(item.pr_detail, {})
			if pr_item.get("has_provisional_entry"):
				purchase_receipt_doc = frappe.get_cached_doc("Purchase Receipt", item.purchase_receipt)

				# Intentionally passing purchase invoice item to handle partial billing
				purchase_receipt_doc.add_provisional_gl_entry(
					item,
					gl_entries,
					self.doc.posting_date,
					pr_item.get("provisional_account"),
					reverse=1,
					item_amount=(
						(min(item.qty, pr_item.get("qty")) * pr_item.get("rate"))
						* purchase_receipt_doc.get("conversion_rate")
					),
				)

	def update_net_purchase_amount_for_linked_assets(self, item):
		doc = self.doc
		assets = frappe.db.get_all(
			"Asset",
			filters={
				"purchase_invoice": doc.name,
				"item_code": item.item_code,
				"purchase_invoice_item": ("in", [item.name, ""]),
			},
			fields=["name", "asset_quantity"],
		)
		for asset in assets:
			purchase_amount = flt(item.valuation_rate) * asset.asset_quantity
			frappe.db.set_value(
				"Asset",
				asset.name,
				{
					"net_purchase_amount": purchase_amount,
					"purchase_amount": purchase_amount,
				},
			)

	def make_stock_adjustment_entry(self, gl_entries, item, voucher_wise_stock_value, account_currency):
		doc = self.doc
		net_amt_precision = item.precision("base_net_amount")
		val_rate_db_precision = 6 if cint(item.precision("valuation_rate")) <= 6 else 9

		warehouse_debit_amount = flt(
			flt(item.valuation_rate, val_rate_db_precision) * flt(item.qty) * flt(item.conversion_factor),
			net_amt_precision,
		)

		if doc.is_return and doc.update_stock and (doc.is_internal_supplier or not doc.return_against):
			net_rate = item.base_net_amount
			if item.sales_incoming_rate:
				net_rate = item.qty * item.sales_incoming_rate

			stock_amount = net_rate + item.item_tax_amount + flt(item.landed_cost_voucher_amount)
			warehouse_debit_amount = flt(
				voucher_wise_stock_value.get((item.name, item.warehouse)), net_amt_precision
			)

			if flt(stock_amount, net_amt_precision) != flt(warehouse_debit_amount, net_amt_precision):
				cost_of_goods_sold_account = doc.get_company_default("default_expense_account")
				stock_adjustment_amt = stock_amount - warehouse_debit_amount

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": cost_of_goods_sold_account,
							"against": item.expense_account,
							"debit": stock_adjustment_amt,
							"debit_in_transaction_currency": stock_adjustment_amt / doc.conversion_rate,
							"remarks": doc.get("remarks") or _("Stock Adjustment"),
							"cost_center": item.cost_center,
							"project": item.project or doc.project,
						},
						account_currency,
						item=item,
					)
				)

		elif (
			doc.update_stock
			and voucher_wise_stock_value.get((item.name, item.warehouse))
			and warehouse_debit_amount
			!= flt(voucher_wise_stock_value.get((item.name, item.warehouse)), net_amt_precision)
		):
			cost_of_goods_sold_account = doc.get_company_default("default_expense_account")
			stock_amount = flt(voucher_wise_stock_value.get((item.name, item.warehouse)), net_amt_precision)
			stock_adjustment_amt = warehouse_debit_amount - stock_amount

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": cost_of_goods_sold_account,
						"against": item.expense_account,
						"debit": stock_adjustment_amt,
						"debit_in_transaction_currency": stock_adjustment_amt / doc.conversion_rate,
						"remarks": doc.get("remarks") or _("Stock Adjustment"),
						"cost_center": item.cost_center,
						"project": item.project or doc.project,
					},
					account_currency,
					item=item,
				)
			)

			warehouse_debit_amount = stock_amount

		return warehouse_debit_amount

	def make_tax_gl_entries(self, gl_entries):
		doc = self.doc
		tax_service = TaxService(doc)
		valuation_tax = {}

		for tax in doc.get("taxes"):
			amount, base_amount = tax_service.get_tax_amounts(tax, None)
			if tax.category in ("Total", "Valuation and Total") and flt(base_amount):
				account_currency = get_account_currency(tax.account_head)
				dr_or_cr = "debit" if tax.add_deduct_tax == "Add" else "credit"
				gl_entries.append(
					self.get_gl_dict(
						{
							"account": tax.account_head,
							"against": doc.supplier,
							dr_or_cr: base_amount,
							dr_or_cr + "_in_account_currency": base_amount
							if account_currency == doc.company_currency
							else amount,
							dr_or_cr + "_in_transaction_currency": amount,
							"cost_center": tax.cost_center,
						},
						account_currency,
						item=tax,
					)
				)

			if (
				doc.is_opening == "No"
				and tax.category in ("Valuation", "Valuation and Total")
				and flt(base_amount)
				and not doc.is_internal_transfer()
			):
				if doc.auto_accounting_for_stock and not tax.cost_center:
					frappe.throw(
						_("Cost Center is required in row {0} in Taxes table for type {1}").format(
							tax.idx, _(tax.category)
						)
					)
				valuation_tax.setdefault(tax.name, 0)
				valuation_tax[tax.name] += (tax.add_deduct_tax == "Add" and 1 or -1) * flt(base_amount)

		if doc.is_opening == "No" and doc.negative_expense_to_be_booked and valuation_tax:
			total_valuation_amount = sum(valuation_tax.values())
			amount_including_divisional_loss = doc.negative_expense_to_be_booked
			i = 1
			for tax in doc.get("taxes"):
				if valuation_tax.get(tax.name):
					if i == len(valuation_tax):
						applicable_amount = amount_including_divisional_loss
					else:
						applicable_amount = doc.negative_expense_to_be_booked * (
							valuation_tax[tax.name] / total_valuation_amount
						)
						amount_including_divisional_loss -= applicable_amount

					gl_entries.append(
						self.get_gl_dict(
							{
								"account": tax.account_head,
								"cost_center": tax.cost_center,
								"against": doc.supplier,
								"credit": applicable_amount,
								"credit_in_transaction_currency": flt(
									applicable_amount / doc.conversion_rate,
									frappe.get_precision("Purchase Invoice Item", "item_tax_amount"),
								),
								"remarks": doc.remarks or _("Accounting Entry for Stock"),
							},
							item=tax,
						)
					)
					i += 1

		if doc.auto_accounting_for_stock and doc.update_stock and valuation_tax:
			for tax in doc.get("taxes"):
				if valuation_tax.get(tax.name):
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": tax.account_head,
								"cost_center": tax.cost_center,
								"against": doc.supplier,
								"credit": valuation_tax[tax.name],
								"credit_in_transaction_currency": flt(
									valuation_tax[tax.name] / doc.conversion_rate,
									frappe.get_precision("Purchase Invoice Item", "item_tax_amount"),
								),
								"remarks": doc.remarks or _("Accounting Entry for Stock"),
							},
							item=tax,
						)
					)

	def make_internal_transfer_gl_entries(self, gl_entries):
		doc = self.doc
		if doc.is_internal_transfer() and flt(doc.base_total_taxes_and_charges):
			account_currency = get_account_currency(doc.unrealized_profit_loss_account)
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": doc.unrealized_profit_loss_account,
						"against": doc.supplier,
						"credit": flt(doc.total_taxes_and_charges),
						"credit_in_transaction_currency": flt(doc.total_taxes_and_charges),
						"credit_in_account_currency": flt(doc.base_total_taxes_and_charges),
						"cost_center": doc.cost_center,
					},
					account_currency,
					item=doc,
				)
			)

	def make_gl_entries_for_tax_withholding(self, gl_entries):
		"""Separate supplier GL entry for tax withholding (TDS) — not part of the supplier invoice amount."""
		doc = self.doc
		if not doc.apply_tds:
			return

		for row in doc.get("taxes"):
			if not row.is_tax_withholding_account or not row.tax_amount:
				continue

			base_tds_amount = row.base_tax_amount_after_discount_amount
			tds_amount = row.tax_amount_after_discount_amount

			self.add_supplier_gl_entry(gl_entries, base_tds_amount, tds_amount)
			self.add_supplier_gl_entry(
				gl_entries,
				-base_tds_amount,
				-tds_amount,
				against_account=row.account_head,
				remarks=_("TDS Deducted"),
				skip_merge=True,
			)

	def make_payment_gl_entries(self, gl_entries):
		doc = self.doc
		if cint(doc.is_paid) and doc.cash_bank_account and doc.paid_amount:
			against_voucher = doc.name
			if doc.is_return and doc.return_against and not doc.update_outstanding_for_self:
				against_voucher = doc.return_against
			bank_account_currency = get_account_currency(doc.cash_bank_account)

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": doc.credit_to,
						"party_type": "Supplier",
						"party": doc.supplier,
						"against": doc.cash_bank_account,
						"debit": doc.base_paid_amount,
						"debit_in_account_currency": doc.base_paid_amount
						if doc.party_account_currency == doc.company_currency
						else doc.paid_amount,
						"debit_in_transaction_currency": doc.paid_amount,
						"against_voucher": against_voucher,
						"against_voucher_type": doc.doctype,
						"cost_center": doc.cost_center,
						"project": doc.project,
					},
					doc.party_account_currency,
					item=doc,
				)
			)

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": doc.cash_bank_account,
						"against": doc.supplier,
						"credit": doc.base_paid_amount,
						"credit_in_account_currency": doc.base_paid_amount
						if bank_account_currency == doc.company_currency
						else doc.paid_amount,
						"credit_in_transaction_currency": doc.paid_amount,
						"cost_center": doc.cost_center,
					},
					bank_account_currency,
					item=doc,
				)
			)

	def make_write_off_gl_entry(self, gl_entries):
		doc = self.doc
		if doc.write_off_account and flt(doc.write_off_amount):
			write_off_account_currency = get_account_currency(doc.write_off_account)

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": doc.credit_to,
						"party_type": "Supplier",
						"party": doc.supplier,
						"against": doc.write_off_account,
						"debit": doc.base_write_off_amount,
						"debit_in_account_currency": doc.base_write_off_amount
						if doc.party_account_currency == doc.company_currency
						else doc.write_off_amount,
						"debit_in_transaction_currency": doc.write_off_amount,
						"against_voucher": doc.return_against
						if cint(doc.is_return) and doc.return_against
						else doc.name,
						"against_voucher_type": doc.doctype,
						"cost_center": doc.cost_center,
						"project": doc.project,
					},
					doc.party_account_currency,
					item=doc,
				)
			)
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": doc.write_off_account,
						"against": doc.supplier,
						"credit": flt(doc.base_write_off_amount),
						"credit_in_account_currency": doc.base_write_off_amount
						if write_off_account_currency == doc.company_currency
						else doc.write_off_amount,
						"credit_in_transaction_currency": doc.write_off_amount,
						"cost_center": doc.cost_center or doc.write_off_cost_center,
					},
					item=doc,
				)
			)

	def make_gle_for_rounding_adjustment(self, gl_entries):
		doc = self.doc
		if not doc.is_internal_transfer() and doc.rounding_adjustment and doc.base_rounding_adjustment:
			(
				round_off_account,
				round_off_cost_center,
				round_off_for_opening,
			) = get_round_off_account_and_cost_center(
				doc.company, "Purchase Invoice", doc.name, doc.use_company_roundoff_cost_center
			)

			if doc.is_opening == "Yes" and doc.rounding_adjustment:
				if not round_off_for_opening:
					frappe.throw(
						_(
							"Opening Invoice has rounding adjustment of {0}.<br><br> '{1}' account is required to post these values. Please set it in Company: {2}.<br><br> Or, '{3}' can be enabled to not post any rounding adjustment."
						).format(
							frappe.bold(doc.rounding_adjustment),
							frappe.bold("Round Off for Opening"),
							get_link_to_form("Company", doc.company),
							frappe.bold("Disable Rounded Total"),
						)
					)
				else:
					round_off_account = round_off_for_opening

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": round_off_account,
						"against": doc.supplier,
						"debit_in_account_currency": doc.rounding_adjustment,
						"debit": doc.base_rounding_adjustment,
						"cost_center": round_off_cost_center
						if doc.use_company_roundoff_cost_center
						else (doc.cost_center or round_off_cost_center),
					},
					item=doc,
				)
			)
