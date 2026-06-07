# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, get_link_to_form

import erpnext
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center
from erpnext.accounts.services.base_gl_composer import BaseGLComposer
from erpnext.accounts.services.taxes import TaxService
from erpnext.accounts.utils import get_account_currency
from erpnext.assets.doctype.asset.depreciation import (
	get_gl_entries_on_asset_disposal,
	get_gl_entries_on_asset_regain,
)


class SalesInvoiceGLComposer(BaseGLComposer):
	"""Assembles the GL entries for a Sales Invoice."""

	def compose(self, inventory_account_map=None):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_regional_gl_entries
		from erpnext.accounts.general_ledger import merge_similar_entries

		doc = self.doc
		gl_entries = []

		self.make_customer_gl_entry(gl_entries)

		self.make_tax_gl_entries(gl_entries)
		self.make_internal_transfer_gl_entries(gl_entries)

		self.make_item_gl_entries(gl_entries)

		disable_sdbnb_in_sr = frappe.get_cached_value("Company", doc.company, "disable_sdbnb_in_sr")

		if not (doc.is_return and disable_sdbnb_in_sr):
			self.stock_delivered_but_not_billed_gl_entries(gl_entries)

		self.make_precision_loss_gl_entry(gl_entries)
		self.make_discount_gl_entries(gl_entries)

		gl_entries = make_regional_gl_entries(gl_entries, doc)

		# merge gl entries before adding pos entries
		gl_entries = merge_similar_entries(gl_entries)

		self.make_loyalty_point_redemption_gle(gl_entries)
		self.make_pos_gl_entries(gl_entries)

		self.make_write_off_gl_entry(gl_entries)
		self.make_gle_for_rounding_adjustment(gl_entries)

		doc.set_transaction_currency_and_rate_in_gl_map(gl_entries)
		return gl_entries

	def make_precision_loss_gl_entry(self, gl_entries):
		doc = self.doc
		(
			round_off_account,
			round_off_cost_center,
			_round_off_for_opening,
		) = get_round_off_account_and_cost_center(
			doc.company, "Sales Invoice", doc.name, doc.use_company_roundoff_cost_center
		)

		precision_loss = doc.get("base_net_total") - flt(
			doc.get("net_total") * doc.conversion_rate, doc.precision("net_total")
		)

		if precision_loss:
			gl_entries.append(
				doc.get_gl_dict(
					{
						"account": round_off_account,
						"against": doc.customer,
						"debit": precision_loss,
						"cost_center": round_off_cost_center
						if doc.use_company_roundoff_cost_center
						else doc.cost_center or round_off_cost_center,
						"remarks": _("Net total calculation precision loss"),
					}
				)
			)

	def make_discount_gl_entries(self, gl_entries):
		doc = self.doc
		enable_discount_accounting = cint(
			frappe.get_single_value("Selling Settings", "enable_discount_accounting")
		)

		if enable_discount_accounting:
			for item in doc.get("items"):
				if item.get("discount_amount") and item.get("discount_account"):
					discount_amount = item.discount_amount * item.qty
					income_account = (
						item.income_account
						if (not item.enable_deferred_revenue or doc.is_return)
						else item.deferred_revenue_account
					)

					account_currency = get_account_currency(item.discount_account)
					gl_entries.append(
						doc.get_gl_dict(
							{
								"account": item.discount_account,
								"against": doc.customer,
								"debit": flt(
									discount_amount * doc.get("conversion_rate"),
									item.precision("discount_amount"),
								),
								"debit_in_transaction_currency": flt(
									discount_amount, item.precision("discount_amount")
								),
								"cost_center": item.cost_center,
								"project": item.project,
							},
							account_currency,
							item=item,
						)
					)

					account_currency = get_account_currency(income_account)
					gl_entries.append(
						doc.get_gl_dict(
							{
								"account": income_account,
								"against": doc.customer,
								"credit": flt(
									discount_amount * doc.get("conversion_rate"),
									item.precision("discount_amount"),
								),
								"credit_in_transaction_currency": flt(
									discount_amount, item.precision("discount_amount")
								),
								"cost_center": item.cost_center,
								"project": item.project or doc.project,
							},
							account_currency,
							item=item,
						)
					)

		if (
			(enable_discount_accounting or doc.get("is_cash_or_non_trade_discount"))
			and doc.get("additional_discount_account")
			and doc.get("discount_amount")
		):
			gl_entries.append(
				doc.get_gl_dict(
					{
						"account": doc.additional_discount_account,
						"against": doc.customer,
						"debit": doc.base_discount_amount,
						"cost_center": doc.cost_center or erpnext.get_default_cost_center(doc.company),
					},
					item=doc,
				)
			)

	def stock_delivered_but_not_billed_gl_entries(self, gl_entries):
		doc = self.doc
		if doc.update_stock or not cint(erpnext.is_perpetual_inventory_enabled(doc.company)):
			return

		for item in doc.get("items"):
			if not item.delivery_note and not item.dn_detail:
				continue

			if not frappe.get_cached_value("Item", item.item_code, "is_stock_item"):
				continue

			dn_expense_account = frappe.get_cached_value(
				"Delivery Note Item", item.dn_detail, "expense_account"
			)
			if (
				not dn_expense_account
				or frappe.get_cached_value("Account", dn_expense_account, "account_type")
				!= "Stock Delivered But Not Billed"
				or not item.expense_account
				or dn_expense_account == item.expense_account
			):
				continue

			delivery_note = item.delivery_note or frappe.get_cached_value(
				"Delivery Note Item", item.dn_detail, "parent"
			)
			if not delivery_note:
				continue

			item_g = frappe.get_cached_value(
				"Stock Ledger Entry",
				{
					"voucher_no": delivery_note,
					"voucher_detail_no": item.dn_detail,
					"item_code": item.item_code,
					"is_cancelled": 0,
				},
				["stock_value_difference", "actual_qty"],
				as_dict=True,
			)

			if not item_g or not flt(item_g.actual_qty):
				continue
			valuation_rate = flt(item_g.stock_value_difference) / flt(item_g.actual_qty)
			valuation_amount = valuation_rate * item.stock_qty
			dn_account_currency = get_account_currency(dn_expense_account)
			item_account_currency = get_account_currency(item.expense_account)

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": dn_expense_account,
						"against": item.expense_account,
						"credit": flt(valuation_amount),
						"credit_in_account_currency": flt(valuation_amount),
						"cost_center": item.cost_center,
					},
					dn_account_currency,
					item=item,
				)
			)
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": item.expense_account,
						"against": dn_expense_account,
						"debit": flt(valuation_amount),
						"debit_in_account_currency": flt(valuation_amount),
						"cost_center": item.cost_center,
					},
					item_account_currency,
					item=item,
				)
			)

	def make_customer_gl_entry(self, gl_entries):
		doc = self.doc
		# Checked both rounding_adjustment and rounded_total
		# because rounded_total had value even before introduction of posting GLE based on rounded total
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
			against_voucher = doc.name
			if doc.is_return and doc.return_against and not doc.update_outstanding_for_self:
				against_voucher = doc.return_against

			# Did not use base_grand_total to book rounding loss gle
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": doc.debit_to,
						"party_type": "Customer",
						"party": doc.customer,
						"due_date": doc.due_date,
						"against": doc.against_income_account,
						"debit": base_grand_total,
						"debit_in_account_currency": base_grand_total
						if doc.party_account_currency == doc.company_currency
						else grand_total,
						"debit_in_transaction_currency": grand_total,
						"against_voucher": against_voucher,
						"against_voucher_type": doc.doctype,
						"cost_center": doc.cost_center,
						"project": doc.project,
					},
					doc.party_account_currency,
					item=doc,
				)
			)

	def make_tax_gl_entries(self, gl_entries):
		doc = self.doc
		tax_service = TaxService(doc)
		enable_discount_accounting = cint(
			frappe.get_single_value("Selling Settings", "enable_discount_accounting")
		)

		for tax in doc.get("taxes"):
			amount, base_amount = tax_service.get_tax_amounts(tax, enable_discount_accounting)

			if flt(tax.base_tax_amount_after_discount_amount):
				account_currency = get_account_currency(tax.account_head)
				gl_entries.append(
					self.get_gl_dict(
						{
							"account": tax.account_head,
							"against": doc.customer,
							"credit": flt(base_amount, tax.precision("tax_amount_after_discount_amount")),
							"credit_in_account_currency": (
								flt(base_amount, tax.precision("base_tax_amount_after_discount_amount"))
								if account_currency == doc.company_currency
								else flt(amount, tax.precision("tax_amount_after_discount_amount"))
							),
							"credit_in_transaction_currency": flt(
								amount, tax.precision("tax_amount_after_discount_amount")
							),
							"cost_center": tax.cost_center,
						},
						account_currency,
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
						"against": doc.customer,
						"debit": flt(doc.total_taxes_and_charges),
						"debit_in_account_currency": flt(doc.base_total_taxes_and_charges),
						"debit_in_transaction_currency": flt(doc.total_taxes_and_charges),
						"cost_center": doc.cost_center,
					},
					account_currency,
					item=doc,
				)
			)

	def make_item_gl_entries(self, gl_entries):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

		doc = self.doc
		tax_service = TaxService(doc)
		# income account gl entries
		enable_discount_accounting = cint(
			frappe.get_single_value("Selling Settings", "enable_discount_accounting")
		)

		for item in doc.get("items"):
			if (
				flt(item.base_net_amount, item.precision("base_net_amount"))
				or item.is_fixed_asset
				or enable_discount_accounting
			):
				# Do not book income for transfer within same company
				if doc.is_internal_transfer():
					continue

				if item.is_fixed_asset and item.asset:
					self.get_gl_entries_for_fixed_asset(item, gl_entries)
				else:
					income_account = (
						item.income_account
						if (not item.enable_deferred_revenue or doc.is_return)
						else item.deferred_revenue_account
					)

					amount, base_amount = tax_service.get_amount_and_base_amount(
						item, enable_discount_accounting
					)

					account_currency = get_account_currency(income_account)
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": income_account,
								"against": doc.customer,
								"credit": flt(base_amount, item.precision("base_net_amount")),
								"credit_in_account_currency": (
									flt(base_amount, item.precision("base_net_amount"))
									if account_currency == doc.company_currency
									else flt(amount, item.precision("net_amount"))
								),
								"credit_in_transaction_currency": flt(amount, item.precision("net_amount")),
								"cost_center": item.cost_center,
								"project": item.project or doc.project,
							},
							account_currency,
							item=item,
						)
					)

		# expense account gl entries
		if cint(doc.update_stock) and erpnext.is_perpetual_inventory_enabled(doc.company):
			gl_entries += super(SalesInvoice, doc).get_gl_entries()

	def get_gl_entries_for_fixed_asset(self, item, gl_entries):
		doc = self.doc
		asset = frappe.get_cached_doc("Asset", item.asset)

		if doc.is_return:
			fixed_asset_gl_entries = get_gl_entries_on_asset_regain(
				asset,
				item.base_net_amount,
				item.finance_book,
				doc.get("doctype"),
				doc.get("name"),
				doc.get("posting_date"),
			)
		else:
			fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(
				asset,
				item.base_net_amount,
				item.finance_book,
				doc.get("doctype"),
				doc.get("name"),
				doc.get("posting_date"),
			)

		for gle in fixed_asset_gl_entries:
			gle["against"] = doc.customer
			gl_entries.append(self.get_gl_dict(gle, item=item))

	def make_loyalty_point_redemption_gle(self, gl_entries):
		doc = self.doc
		if cint(doc.redeem_loyalty_points and doc.loyalty_points and not doc.is_consolidated):
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": doc.debit_to,
						"party_type": "Customer",
						"party": doc.customer,
						"against": "Expense account - "
						+ cstr(doc.loyalty_redemption_account)
						+ " for the Loyalty Program",
						"credit": doc.loyalty_amount,
						"credit_in_transaction_currency": doc.loyalty_amount,
						"against_voucher": doc.return_against if cint(doc.is_return) else doc.name,
						"against_voucher_type": doc.doctype,
						"cost_center": doc.cost_center,
					},
					item=doc,
				)
			)
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": doc.loyalty_redemption_account,
						"cost_center": doc.cost_center or doc.loyalty_redemption_cost_center,
						"against": doc.customer,
						"debit": doc.loyalty_amount,
						"debit_in_transaction_currency": doc.loyalty_amount,
						"remark": "Loyalty Points redeemed by the customer",
					},
					item=doc,
				)
			)

	def make_pos_gl_entries(self, gl_entries):
		doc = self.doc
		if cint(doc.is_pos):
			skip_change_gl_entries = not cint(
				frappe.get_single_value("POS Settings", "post_change_gl_entries")
			)

			for payment_mode in doc.payments:
				if skip_change_gl_entries and payment_mode.account == doc.account_for_change_amount:
					payment_mode.base_amount -= flt(doc.change_amount)

				against_voucher = doc.name
				if doc.is_return and doc.return_against and not doc.update_outstanding_for_self:
					against_voucher = doc.return_against

				if payment_mode.base_amount:
					# POS, make payment entries
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": doc.debit_to,
								"party_type": "Customer",
								"party": doc.customer,
								"against": payment_mode.account,
								"credit": payment_mode.base_amount,
								"credit_in_account_currency": payment_mode.base_amount
								if doc.party_account_currency == doc.company_currency
								else payment_mode.amount,
								"credit_in_transaction_currency": payment_mode.amount,
								"against_voucher": against_voucher,
								"against_voucher_type": doc.doctype,
								"cost_center": doc.cost_center,
							},
							doc.party_account_currency,
							item=doc,
						)
					)

					payment_mode_account_currency = get_account_currency(payment_mode.account)
					gl_entries.append(
						self.get_gl_dict(
							{
								"account": payment_mode.account,
								"against": doc.customer,
								"debit": payment_mode.base_amount,
								"debit_in_account_currency": payment_mode.base_amount
								if payment_mode_account_currency == doc.company_currency
								else payment_mode.amount,
								"debit_in_transaction_currency": payment_mode.amount,
								"cost_center": doc.cost_center,
							},
							payment_mode_account_currency,
							item=doc,
						)
					)

			if not skip_change_gl_entries:
				gl_entries.extend(self.get_gle_for_change_amount())

	def get_gle_for_change_amount(self) -> list[dict]:
		doc = self.doc
		if not doc.change_amount:
			return []

		if not doc.account_for_change_amount:
			frappe.throw(_("Please set Account for Change Amount"), title=_("Mandatory Field"))

		return [
			self.get_gl_dict(
				{
					"account": doc.debit_to,
					"party_type": "Customer",
					"party": doc.customer,
					"against": doc.account_for_change_amount,
					"debit": flt(doc.base_change_amount),
					"debit_in_account_currency": flt(doc.base_change_amount)
					if doc.party_account_currency == doc.company_currency
					else flt(doc.change_amount),
					"debit_in_transaction_currency": flt(doc.change_amount),
					"against_voucher": doc.return_against
					if cint(doc.is_return) and doc.return_against
					else doc.name,
					"against_voucher_type": doc.doctype,
					"cost_center": doc.cost_center,
					"project": doc.project,
				},
				doc.party_account_currency,
				item=doc,
			),
			self.get_gl_dict(
				{
					"account": doc.account_for_change_amount,
					"against": doc.customer,
					"credit": doc.base_change_amount,
					"credit_in_transaction_currency": doc.change_amount,
					"cost_center": doc.cost_center,
				},
				item=doc,
			),
		]

	def make_write_off_gl_entry(self, gl_entries):
		doc = self.doc
		# write off entries, applicable if only pos
		if (
			doc.is_pos
			and doc.write_off_account
			and flt(doc.write_off_amount, doc.precision("write_off_amount"))
		):
			write_off_account_currency = get_account_currency(doc.write_off_account)
			default_cost_center = frappe.get_cached_value("Company", doc.company, "cost_center")

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": doc.debit_to,
						"party_type": "Customer",
						"party": doc.customer,
						"against": doc.write_off_account,
						"credit": flt(doc.base_write_off_amount, doc.precision("base_write_off_amount")),
						"credit_in_account_currency": (
							flt(doc.base_write_off_amount, doc.precision("base_write_off_amount"))
							if doc.party_account_currency == doc.company_currency
							else flt(doc.write_off_amount, doc.precision("write_off_amount"))
						),
						"credit_in_transaction_currency": flt(
							doc.write_off_amount, doc.precision("write_off_amount")
						),
						"against_voucher": doc.return_against if cint(doc.is_return) else doc.name,
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
						"against": doc.customer,
						"debit": flt(doc.base_write_off_amount, doc.precision("base_write_off_amount")),
						"debit_in_account_currency": (
							flt(doc.base_write_off_amount, doc.precision("base_write_off_amount"))
							if write_off_account_currency == doc.company_currency
							else flt(doc.write_off_amount, doc.precision("write_off_amount"))
						),
						"debit_in_transaction_currency": flt(
							doc.write_off_amount, doc.precision("write_off_amount")
						),
						"cost_center": doc.cost_center or doc.write_off_cost_center or default_cost_center,
					},
					write_off_account_currency,
					item=doc,
				)
			)

	def make_gle_for_rounding_adjustment(self, gl_entries):
		doc = self.doc
		if (
			flt(doc.rounding_adjustment, doc.precision("rounding_adjustment"))
			and doc.base_rounding_adjustment
			and not doc.is_internal_transfer()
		):
			(
				round_off_account,
				round_off_cost_center,
				round_off_for_opening,
			) = get_round_off_account_and_cost_center(
				doc.company, "Sales Invoice", doc.name, doc.use_company_roundoff_cost_center
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
						"against": doc.customer,
						"credit_in_account_currency": flt(
							doc.rounding_adjustment, doc.precision("rounding_adjustment")
						),
						"credit_in_transaction_currency": flt(
							doc.rounding_adjustment, doc.precision("rounding_adjustment")
						),
						"credit": flt(
							doc.base_rounding_adjustment, doc.precision("base_rounding_adjustment")
						),
						"cost_center": round_off_cost_center
						if doc.use_company_roundoff_cost_center
						else (doc.cost_center or round_off_cost_center),
					},
					item=doc,
				)
			)
