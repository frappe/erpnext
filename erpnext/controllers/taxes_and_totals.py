# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import json
import frappe, erpnext
from frappe import _, scrub
from frappe.utils import cint, flt, round_based_on_smallest_currency_fraction
from erpnext.controllers.accounts_controller import validate_conversion_rate, \
	validate_taxes_and_charges, validate_inclusive_tax
from six import iteritems
from erpnext.stock.get_item_details import _get_item_tax_template
from erpnext.accounts.doctype.pricing_rule.utils import get_applied_pricing_rules


class calculate_taxes_and_totals(object):
	def __init__(self, doc):
		self.doc = doc
		self.calculate()

	def calculate(self):
		if not len(self.doc.get("items")):
			return

		self.discount_amount_applied = False
		self._calculate()

		if self.doc.meta.get_field("discount_amount"):
			self.set_discount_amount()
			self.apply_discount_amount()

		if self.doc.doctype in ["Sales Invoice", "Purchase Invoice"]:
			self.calculate_total_advance()

		if self.doc.doctype in ["Sales Order", "Purchase Order"] and self.doc.docstatus == 0:
			self.advance_paid = 0

		if self.doc.meta.get_field("other_charges_calculation"):
			self.set_item_wise_tax_breakup()

	def _calculate(self):
		self.validate_conversion_rate()
		self.calculate_item_values()
		self.validate_item_tax_template()
		self.initialize_taxes()
		self.determine_exclusive_rate()
		self.calculate_net_total()
		self.calculate_taxes()
		self.manipulate_grand_total_for_inclusive_tax()
		self.calculate_tax_inclusive_rate()
		self.calculate_totals()
		self._cleanup()
		self.calculate_total_net_weight()

	def validate_item_tax_template(self):
		for item in self.doc.get('items'):
			if item.item_code and item.get('item_tax_template'):
				item_doc = frappe.get_cached_doc("Item", item.item_code)
				args = {
					'tax_category': self.doc.get('tax_category'),
					'posting_date': self.doc.get('posting_date'),
					'bill_date': self.doc.get('bill_date'),
					'transaction_date': self.doc.get('transaction_date')
				}

				item_group = item_doc.item_group
				item_group_taxes = []

				while item_group:
					item_group_doc = frappe.get_cached_doc('Item Group', item_group)
					item_group_taxes += item_group_doc.taxes or []
					item_group = item_group_doc.parent_item_group

				item_taxes = item_doc.taxes or []

				if not item_group_taxes and (not item_taxes):
					# No validation if no taxes in item or item group
					continue

				taxes = _get_item_tax_template(args, item_taxes + item_group_taxes, for_validate=True)

				if item.item_tax_template not in taxes:
					frappe.msgprint(_("Row {0}: Invalid Item Tax Template for item {1}").format(
						item.idx, frappe.bold(item.item_code)
					))

	def validate_conversion_rate(self):
		# validate conversion rate
		company_currency = erpnext.get_company_currency(self.doc.company)
		if not self.doc.currency or self.doc.currency == company_currency:
			self.doc.currency = company_currency
			self.doc.conversion_rate = 1.0
		else:
			validate_conversion_rate(self.doc.currency, self.doc.conversion_rate,
				self.doc.meta.get_label("conversion_rate"), self.doc.company)

		self.doc.conversion_rate = flt(self.doc.conversion_rate)

	def calculate_item_values(self):
		if not self.discount_amount_applied:
			for item in self.doc.get("items"):
				has_margin_field = item.doctype in ['Quotation Item', 'Sales Order Item', 'Delivery Note Item', 'Sales Invoice Item']

				exclude_round_fieldnames = []
				if has_margin_field and item.margin_type == "Percentage":
					exclude_round_fieldnames.append('margin_rate_or_amount')
				self.doc.round_floats_in(item, excluding=exclude_round_fieldnames)

				if item.discount_percentage == 100:
					item.rate = 0.0
				elif item.price_list_rate:
					if not item.rate or (item.pricing_rules and item.discount_percentage > 0):
						item.rate = flt(item.price_list_rate *
							(1.0 - (item.discount_percentage / 100.0)), item.precision("rate"))
						item.discount_amount = item.price_list_rate * (item.discount_percentage / 100.0)
					elif item.discount_amount and item.pricing_rules:
						item.rate =  item.price_list_rate - item.discount_amount

				if has_margin_field:
					item.rate_with_margin, item.base_rate_with_margin = self.calculate_margin(item)

				if has_margin_field and flt(item.rate_with_margin):
					rate_before_discount = item.rate_with_margin
					item.rate = flt(item.rate_with_margin * (1.0 - (item.discount_percentage / 100.0)), item.precision("rate"))
					item.discount_amount = item.rate_with_margin - item.rate
				elif flt(item.price_list_rate):
					rate_before_discount = item.price_list_rate
					item.discount_amount = item.price_list_rate - item.rate
				else:
					rate_before_discount = item.rate
					item.discount_amount = 0
					item.discount_percentage = 0

				item.amount_before_discount = flt(rate_before_discount * item.qty, item.precision("amount_before_discount"))
				item.amount = flt(item.rate * item.qty,	item.precision("amount"))
				item.total_discount = flt(item.amount_before_discount - item.amount, item.precision("total_discount"))

				has_depreciation_field = item.meta.has_field('depreciation_amount')
				if has_depreciation_field:
					item.depreciation_amount = flt(item.amount_before_discount * flt(item.depreciation_percentage) / 100,
						item.precision("depreciation_amount"))
					self._set_in_company_currency(item, ['depreciation_amount'])

				if self.doc.doctype == "Sales Invoice":
					item.amount_before_depreciation = item.amount_before_discount
					self._set_in_company_currency(item, ['amount_before_depreciation'])

					if self.doc.depreciation_type:
						depreciation_on_discount = flt(item.total_discount * flt(item.depreciation_percentage) / 100,
							item.precision("amount"))
						depreciation_adjusted_discount = item.total_discount - depreciation_on_discount

						if self.doc.depreciation_type == "After Depreciation Amount":
							item.amount_before_discount = flt(item.amount_before_discount - item.depreciation_amount,
								item.precision("amount_before_discount"))
							item.amount = flt(item.amount_before_discount - depreciation_adjusted_discount, item.precision("amount"))
						else:
							item.amount_before_discount = flt(item.depreciation_amount, item.precision("amount_before_discount"))
							item.amount = flt(item.amount_before_discount - depreciation_on_discount, item.precision("amount"))

						item.total_discount = flt(item.amount_before_discount - item.amount, item.precision("total_discount"))

					item.tax_exclusive_depreciation_amount = item.depreciation_amount
					item.tax_exclusive_amount_before_depreciation = item.amount_before_depreciation

				item.taxable_rate = rate_before_discount if cint(item.apply_discount_after_taxes) else item.rate
				item.taxable_amount = item.amount_before_discount if cint(item.apply_discount_after_taxes) else item.amount
				item.taxable_rate = flt(item.taxable_amount / item.qty, item.precision("taxable_rate")) if item.qty else item.taxable_rate

				item.net_rate = item.rate
				item.net_amount = item.amount
				item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate")) if item.qty else item.net_rate

				item.item_taxes_and_charges = 0
				item.tax_inclusive_amount = 0
				item.tax_inclusive_rate = 0

				item.tax_exclusive_price_list_rate = item.price_list_rate
				item.tax_exclusive_rate = item.rate
				item.tax_exclusive_amount = item.amount
				item.tax_exclusive_discount_amount = item.discount_amount
				item.tax_exclusive_amount_before_discount = item.amount_before_discount
				item.tax_exclusive_total_discount = item.total_discount
				if has_margin_field:
					item.tax_exclusive_rate_with_margin = item.rate_with_margin
					item.base_tax_exclusive_rate_with_margin = item.base_rate_with_margin

				self._set_in_company_currency(item, ["price_list_rate", "rate", "amount",
					"taxable_rate", "taxable_amount", "net_rate", "net_amount",
					"tax_exclusive_price_list_rate", "tax_exclusive_rate", "tax_exclusive_amount",
					"amount_before_discount", "total_discount", "tax_exclusive_amount_before_discount", "tax_exclusive_total_discount"])

				item.item_tax_amount = 0.0

	def _set_in_company_currency(self, doc, fields, do_not_round_before_conversion=False):
		"""set values in base currency"""
		for f in fields:
			v = flt(doc.get(f)) if do_not_round_before_conversion else flt(doc.get(f), doc.precision(f))
			val = flt(v * self.doc.conversion_rate, doc.precision("base_" + f))
			doc.set("base_" + f, val)

	def should_round_transaction_currency(self):
		company_currency = erpnext.get_company_currency(self.doc.company)
		return not cint(self.doc.get("calculate_tax_on_company_currency"))\
			or not self.doc.currency or self.doc.currency == company_currency

	def initialize_taxes(self):
		for tax in self.doc.get("taxes"):
			if not self.discount_amount_applied:
				validate_taxes_and_charges(tax)
				validate_inclusive_tax(tax, self.doc)

			tax.item_wise_tax_detail = {}
			tax_fields = ["total", "tax_amount_after_discount_amount",
				"tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"]

			if tax.charge_type not in ["Actual", "Weighted Distribution"] and \
				not (self.discount_amount_applied and self.doc.apply_discount_on=="Grand Total"):
					tax_fields.append("tax_amount")

			for fieldname in tax_fields:
				tax.set(fieldname, 0.0)

			if self.should_round_transaction_currency():
				self.doc.round_floats_in(tax)
			else:
				self.doc.round_floats_in(tax, ["rate"])

		for item in self.doc.get("items"):
			item.item_tax_detail = {}
			item.item_taxes_and_charges = 0

	def determine_exclusive_rate(self):
		for item in self.doc.get("items"):
			item.cumulated_tax_fraction = 0

		if not any((cint(tax.included_in_print_rate) for tax in self.doc.get("taxes"))):
			return

		for item in self.doc.get("items"):
			has_margin_field = item.doctype in ['Quotation Item', 'Sales Order Item', 'Delivery Note Item', 'Sales Invoice Item']
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)

			for i, tax in enumerate(self.doc.get("taxes")):
				tax.tax_fraction_for_current_item = self.get_current_tax_fraction(tax, item_tax_map)

				if i==0:
					tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item
				else:
					tax.grand_total_fraction_for_current_item = \
						self.doc.get("taxes")[i-1].grand_total_fraction_for_current_item \
						+ tax.tax_fraction_for_current_item

				item.cumulated_tax_fraction += tax.tax_fraction_for_current_item

			if item.cumulated_tax_fraction and not self.discount_amount_applied:
				item.tax_exclusive_amount = flt(item.amount / (1 + item.cumulated_tax_fraction))
				item.tax_exclusive_rate = flt(item.rate / (1 + item.cumulated_tax_fraction))\
					if not item.qty or item.get('depreciation_percentage') else flt(item.tax_exclusive_amount / item.qty)

				item.tax_exclusive_amount_before_discount = flt(item.amount_before_discount / (1 + item.cumulated_tax_fraction))
				item.tax_exclusive_total_discount = flt(item.tax_exclusive_amount_before_discount - item.tax_exclusive_amount,
					item.precision("tax_exclusive_total_discount"))

				if self.doc.doctype == "Sales Invoice":
					item.tax_exclusive_amount_before_depreciation = flt(item.amount_before_depreciation / (1 + item.cumulated_tax_fraction))
					item.tax_exclusive_depreciation_amount = flt(item.tax_exclusive_amount_before_depreciation * flt(item.depreciation_percentage) / 100,
						item.precision("tax_exclusive_depreciation_amount"))

					self._set_in_company_currency(item, ["tax_exclusive_amount_before_depreciation", "tax_exclusive_depreciation_amount"])

				if item.qty:
					item.tax_exclusive_price_list_rate = flt((item.get('tax_exclusive_amount_before_depreciation') or item.tax_exclusive_amount_before_discount) / item.qty)
				elif item.price_list_rate:
					item.tax_exclusive_price_list_rate = flt(item.price_list_rate / (1 + item.cumulated_tax_fraction))
				else:
					item.tax_exclusive_price_list_rate = 0.0

				if has_margin_field and flt(item.rate_with_margin):
					item.tax_exclusive_rate_with_margin = flt(item.rate_with_margin / (1 + item.cumulated_tax_fraction))
					item.base_tax_exclusive_rate_with_margin = flt(item.tax_exclusive_rate_with_margin * self.doc.conversion_rate)
					item.tax_exclusive_discount_amount = flt(item.tax_exclusive_rate_with_margin - item.tax_exclusive_rate)
				elif flt(item.tax_exclusive_price_list_rate):
					item.tax_exclusive_discount_amount = flt(item.tax_exclusive_price_list_rate - item.tax_exclusive_rate)

				item.taxable_amount = flt(item.taxable_amount / (1 + item.cumulated_tax_fraction))
				item.taxable_rate = flt(item.taxable_amount / item.qty, item.precision("taxable_rate")) if item.qty else 0.0

				item.net_amount = flt(item.net_amount / (1 + item.cumulated_tax_fraction))
				item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate")) if item.qty else 0.0

				item.discount_percentage = flt(item.discount_percentage,
					item.precision("discount_percentage"))

				self._set_in_company_currency(item, ["taxable_rate", "taxable_amount", "net_rate", "net_amount",
					"tax_exclusive_price_list_rate", "tax_exclusive_rate", "tax_exclusive_amount",
					"tax_exclusive_amount_before_discount", "tax_exclusive_total_discount"])

	def _load_item_tax_rate(self, item_tax_rate):
		return json.loads(item_tax_rate) if item_tax_rate else {}

	def get_current_tax_fraction(self, tax, item_tax_map):
		"""
			Get tax fraction for calculating tax exclusive amount
			from tax inclusive amount
		"""
		current_tax_fraction = 0

		if cint(tax.included_in_print_rate):
			tax_rate = self._get_tax_rate(tax, item_tax_map)

			if tax.charge_type == "On Net Total":
				current_tax_fraction = tax_rate / 100.0

			elif tax.charge_type == "On Previous Row Amount":
				current_tax_fraction = (tax_rate / 100.0) * \
					self.doc.get("taxes")[cint(tax.row_id) - 1].tax_fraction_for_current_item

			elif tax.charge_type == "On Previous Row Total":
				current_tax_fraction = (tax_rate / 100.0) * \
					self.doc.get("taxes")[cint(tax.row_id) - 1].grand_total_fraction_for_current_item

		if getattr(tax, "add_deduct_tax", None):
			current_tax_fraction *= -1.0 if (tax.add_deduct_tax == "Deduct") else 1.0
		return current_tax_fraction

	def _get_tax_rate(self, tax, item_tax_map):
		if tax.account_head in item_tax_map:
			return flt(item_tax_map.get(tax.account_head), self.doc.precision("rate", tax))
		else:
			return tax.rate

	def calculate_net_total(self):
		self.doc.total_qty = self.doc.total = self.doc.base_total = self.doc.net_total = self.doc.base_net_total = 0.0
		self.doc.taxable_total = self.doc.base_taxable_total = 0.0
		self.doc.total_alt_uom_qty = 0
		self.doc.base_tax_exclusive_total = self.doc.tax_exclusive_total = 0.0
		self.doc.base_total_discount = self.doc.total_discount = 0.0
		self.doc.base_total_before_discount = self.doc.total_before_discount = 0.0
		self.doc.base_tax_exclusive_total_before_discount = self.doc.tax_exclusive_total_before_discount = 0.0
		self.doc.base_tax_exclusive_total_discount = self.doc.tax_exclusive_total_discount = 0.0

		has_depreciation_field = self.doc.meta.has_field('total_depreciation')
		if has_depreciation_field:
			self.doc.base_total_depreciation = self.doc.total_depreciation = 0.0

		has_depreciation_adjustment = self.doc.doctype == "Sales Invoice"
		if has_depreciation_adjustment:
			self.doc.base_total_before_depreciation = self.doc.total_before_depreciation = 0.0
			self.doc.base_tax_exclusive_total_before_depreciation = self.doc.tax_exclusive_total_before_depreciation = 0.0
			self.doc.base_tax_exclusive_total_depreciation = self.doc.tax_exclusive_total_depreciation = 0.0

		for item in self.doc.get("items"):
			self.doc.total_qty += item.qty
			self.doc.total_alt_uom_qty += item.alt_uom_qty

			self.doc.total += item.amount
			self.doc.base_total += item.base_amount

			self.doc.tax_exclusive_total += item.tax_exclusive_amount
			self.doc.base_tax_exclusive_total += item.base_tax_exclusive_amount

			self.doc.total_before_discount += item.amount_before_discount
			self.doc.base_total_before_discount += item.base_amount_before_discount
			self.doc.tax_exclusive_total_before_discount += item.tax_exclusive_amount_before_discount
			self.doc.base_tax_exclusive_total_before_discount += item.base_tax_exclusive_amount_before_discount

			self.doc.total_discount += item.total_discount
			self.doc.base_total_discount += item.base_total_discount
			self.doc.tax_exclusive_total_discount += item.tax_exclusive_total_discount
			self.doc.base_tax_exclusive_total_discount += item.base_tax_exclusive_total_discount

			self.doc.taxable_total += item.taxable_amount
			self.doc.base_taxable_total += item.base_taxable_amount

			self.doc.net_total += item.net_amount
			self.doc.base_net_total += item.base_net_amount

			if has_depreciation_field:
				self.doc.total_depreciation += item.depreciation_amount
				self.doc.base_total_depreciation += item.base_depreciation_amount

			if has_depreciation_adjustment:
				self.doc.total_before_depreciation += item.amount_before_depreciation
				self.doc.base_total_before_depreciation += item.base_amount_before_depreciation

				self.doc.tax_exclusive_total_before_depreciation += item.tax_exclusive_amount_before_depreciation
				self.doc.base_tax_exclusive_total_before_depreciation += item.base_tax_exclusive_amount_before_depreciation

				self.doc.tax_exclusive_total_depreciation += item.tax_exclusive_depreciation_amount
				self.doc.base_tax_exclusive_total_depreciation += item.base_tax_exclusive_depreciation_amount

		self.doc.total_discount_after_taxes = self.doc.taxable_total - self.doc.net_total
		self.doc.base_total_discount_after_taxes = self.doc.base_taxable_total - self.doc.base_net_total

		self.doc.round_floats_in(self.doc, ["total", "base_total", "net_total", "base_net_total",
			"taxable_total", "base_taxable_total",
			"total_discount_after_taxes", "base_total_discount_after_taxes",
			"tax_exclusive_total", "base_tax_exclusive_total",
			"total_before_discount", "total_discount", "base_total_before_discount", "base_total_discount",
			"tax_exclusive_total_before_discount", "tax_exclusive_total_discount",
			"base_tax_exclusive_total_before_discount", "base_tax_exclusive_total_discount"])

		if self.doc.doctype == 'Sales Invoice' and self.doc.is_pos:
			self.doc.pos_total_qty = self.doc.total_qty

	def calculate_taxes(self):
		self.doc.rounding_adjustment = 0
		# maintain actual tax rate based on idx
		actual_tax_dict = dict([[tax.idx,
			flt(tax.tax_amount, tax.precision("tax_amount")) if self.should_round_transaction_currency() else tax.tax_amount]
			for tax in self.doc.get("taxes") if tax.charge_type in ["Actual", "Weighted Distribution"]])

		# Tax on Net Total for Weighted Distribution
		weighted_distrubution_tax_on_net_total = {}
		for n, item in enumerate(self.doc.get("items")):
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
			for i, tax in enumerate(self.doc.get("taxes")):
				if tax.charge_type == "Weighted Distribution":
					weighted_distrubution_tax_on_net_total.setdefault(tax.idx, 0.0)
					tax_rate = self._get_tax_rate(tax, item_tax_map)
					weighted_distrubution_tax_on_net_total[tax.idx] += (tax_rate / 100) * item.net_amount

		for n, item in enumerate(self.doc.get("items")):
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
			for i, tax in enumerate(self.doc.get("taxes")):
				# tax_amount represents the amount of tax for the current step
				current_tax_amount = self.get_current_tax_amount(item, tax, item_tax_map, weighted_distrubution_tax_on_net_total)

				# Adjust divisional loss to the last item
				if tax.charge_type in ["Actual", "Weighted Distribution"]:
					actual_tax_dict[tax.idx] -= current_tax_amount
					if n == len(self.doc.get("items")) - 1:
						current_tax_amount += actual_tax_dict[tax.idx]

				# accumulate tax amount into tax.tax_amount
				if tax.charge_type not in ["Actual", "Weighted Distribution"] and \
					not (self.discount_amount_applied and self.doc.apply_discount_on=="Grand Total"):
						tax.tax_amount += current_tax_amount

				# store tax_amount for current item as it will be used for
				# charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount

				# set tax after discount
				tax.tax_amount_after_discount_amount += current_tax_amount

				current_tax_amount = self.get_tax_amount_if_for_valuation_or_deduction(current_tax_amount, tax)

				# note: grand_total_for_current_item contains the contribution of
				# item's amount, previously applied tax and the current tax on that item
				if i==0:
					tax.grand_total_for_current_item = flt(item.taxable_amount + current_tax_amount)
				else:
					tax.grand_total_for_current_item = \
						flt(self.doc.get("taxes")[i-1].grand_total_for_current_item + current_tax_amount)

				# set precision in the last item iteration
				if n == len(self.doc.get("items")) - 1:
					self.round_off_totals(tax)
					self.set_cumulative_total(i, tax)

					self._set_in_company_currency(tax,
						["total", "displayed_total", "tax_amount", "tax_amount_after_discount_amount"],
						not self.should_round_transaction_currency())

					# adjust Discount Amount loss in last tax iteration
					if i == (len(self.doc.get("taxes")) - 1) and self.discount_amount_applied \
						and self.doc.discount_amount and self.doc.apply_discount_on == "Grand Total":
							new_grand_total = self.doc.grand_total - flt(self.doc.discount_amount)
							calculated_grand_total = self.doc.net_total + sum([d.tax_amount_after_discount_amount for d in self.doc.taxes])
							self.doc.rounding_adjustment = flt(new_grand_total - calculated_grand_total,
								self.doc.precision("rounding_adjustment"))

	def get_tax_amount_if_for_valuation_or_deduction(self, tax_amount, tax):
		# if just for valuation, do not add the tax amount in total
		# if tax/charges is for deduction, multiply by -1
		if getattr(tax, "category", None):
			tax_amount = 0.0 if (tax.category == "Valuation") else tax_amount
			if self.doc.doctype in ["Purchase Order", "Purchase Invoice", "Purchase Receipt", "Supplier Quotation"]:
				tax_amount *= -1.0 if (tax.add_deduct_tax == "Deduct") else 1.0
		return tax_amount

	def set_cumulative_total(self, row_idx, tax):
		tax_amount = tax.tax_amount_after_discount_amount
		tax_amount = self.get_tax_amount_if_for_valuation_or_deduction(tax_amount, tax)
		tax_amount_before_discount = tax.tax_amount
		tax_amount_before_discount = self.get_tax_amount_if_for_valuation_or_deduction(tax_amount_before_discount, tax)

		if row_idx == 0:
			tax.total = self.doc.taxable_total + tax_amount

			if not self.discount_amount_applied:
				if self.doc.apply_discount_on == "Grand Total":
					tax.displayed_total = self.doc.taxable_total + tax_amount_before_discount
				else:
					tax.displayed_total = tax.total
		else:
			tax.total = self.doc.get("taxes")[row_idx-1].total + tax_amount

			if not self.discount_amount_applied:
				if self.doc.apply_discount_on == "Grand Total":
					tax.displayed_total = self.doc.get("taxes")[row_idx-1].displayed_total + tax_amount_before_discount
				else:
					tax.displayed_total = tax.total

		if self.should_round_transaction_currency():
			tax.total = flt(tax.total, tax.precision("total"))
			tax.displayed_total = flt(tax.displayed_total, tax.precision("displayed_total"))

	def get_current_tax_amount(self, item, tax, item_tax_map, weighted_distrubution_tax_on_net_total):
		tax_rate = self._get_tax_rate(tax, item_tax_map)
		current_tax_amount = 0.0

		if tax.charge_type in ["Actual", "Weighted Distribution"]:
			# distribute the tax amount proportionally to each item row
			actual = flt(tax.tax_amount, tax.precision("tax_amount")) if self.should_round_transaction_currency()\
				else tax.tax_amount

			if tax.charge_type == "Actual" or not weighted_distrubution_tax_on_net_total.get(tax.idx):
				if self.doc.net_total:
					current_tax_amount = actual * item.net_amount / self.doc.net_total
				else:
					current_tax_amount = actual * item.qty / self.doc.total_qty if self.doc.total_qty else 0
			else:
				tax_on_net_amount = (tax_rate / 100.0) * item.net_amount
				tax_on_net_total = weighted_distrubution_tax_on_net_total.get(tax.idx)
				current_tax_amount = actual * (tax_on_net_amount / tax_on_net_total)

		elif tax.charge_type == "Manual":
			item_key = item.item_code or item.item_name
			current_tax_amount = flt(json.loads(tax.manual_distribution_detail or '{}').get(item_key))
			if self.doc.calculate_tax_on_company_currency:
				current_tax_amount = current_tax_amount / (self.doc.conversion_rate or 1)

			total_net_amount = sum([d.net_amount for d in self.doc.items if (d.item_code or d.item_name) == item_key])
			current_tax_amount *= item.net_amount / total_net_amount if total_net_amount else 0
		elif tax.charge_type == "On Net Total":
			current_tax_amount = (tax_rate / 100.0) * item.taxable_amount
		elif tax.charge_type == "On Previous Row Amount":
			current_tax_amount = (tax_rate / 100.0) * \
				self.doc.get("taxes")[cint(tax.row_id) - 1].tax_amount_for_current_item
		elif tax.charge_type == "On Previous Row Total":
			current_tax_amount = (tax_rate / 100.0) * \
				self.doc.get("taxes")[cint(tax.row_id) - 1].grand_total_for_current_item
		elif tax.charge_type == "On Item Quantity":
			current_tax_amount = tax_rate * item.qty

		self.set_item_wise_tax(item, tax, tax_rate, current_tax_amount)

		return current_tax_amount

	def set_item_wise_tax(self, item, tax, tax_rate, current_tax_amount):
		# store tax breakup for each item
		item.item_taxes_and_charges += current_tax_amount
		item.item_tax_detail.setdefault(tax.name, 0)
		item.item_tax_detail[tax.name] += current_tax_amount

		key = item.item_code or item.item_name
		item_wise_tax_amount = current_tax_amount*self.doc.conversion_rate
		if tax.item_wise_tax_detail.get(key):
			item_wise_tax_amount += tax.item_wise_tax_detail[key][1]

		tax.item_wise_tax_detail[key] = [tax_rate,flt(item_wise_tax_amount)]

	def round_off_totals(self, tax):
		if self.should_round_transaction_currency():
			tax.tax_amount = flt(tax.tax_amount, tax.precision("tax_amount"))
			tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount,
				tax.precision("tax_amount"))

	def manipulate_grand_total_for_inclusive_tax(self):
		# if fully inclusive taxes and diff
		if self.doc.get("taxes") and any([cint(t.included_in_print_rate) for t in self.doc.get("taxes")]):
			last_tax = self.doc.get("taxes")[-1]
			non_inclusive_tax_amount = sum([flt(d.tax_amount_after_discount_amount)
				for d in self.doc.get("taxes") if not d.included_in_print_rate])

			diff = self.doc.total + non_inclusive_tax_amount \
				- flt(last_tax.total, last_tax.precision("total"))

			# If discount amount applied, deduct the discount amount
			# because self.doc.total is always without discount, but last_tax.total is after discount
			if self.discount_amount_applied and self.doc.discount_amount:
				diff -= flt(self.doc.discount_amount)

			diff = flt(diff, self.doc.precision("rounding_adjustment"))

			if diff and abs(diff) <= (5.0 / 10**last_tax.precision("tax_amount")):
				self.doc.rounding_adjustment = diff

	def calculate_tax_inclusive_rate(self):
		for item in self.doc.items:
			item.tax_inclusive_amount = flt(item.tax_exclusive_amount + item.item_taxes_and_charges)
			item.tax_inclusive_rate = flt(item.tax_inclusive_amount / item.qty) if item.qty else 0
			self._set_in_company_currency(item, ['item_taxes_and_charges', 'tax_inclusive_amount', 'tax_inclusive_rate'],
				not self.should_round_transaction_currency())

	def calculate_totals(self):
		self.doc.total_after_taxes = flt(self.doc.get("taxes")[-1].total) + flt(self.doc.rounding_adjustment) \
			if self.doc.get("taxes") else flt(self.doc.taxable_total)

		self.doc.total_taxes_and_charges = self.doc.total_after_taxes - self.doc.taxable_total - flt(self.doc.rounding_adjustment)
		if self.should_round_transaction_currency():
			self.doc.total_taxes_and_charges = flt(self.doc.total_taxes_and_charges, self.doc.precision("total_taxes_and_charges"))

		self._set_in_company_currency(self.doc, ["total_taxes_and_charges", "rounding_adjustment"],
			not self.should_round_transaction_currency())

		if self.doc.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
			self.doc.base_total_after_taxes = flt(self.doc.total_after_taxes * self.doc.conversion_rate) \
				if self.doc.total_taxes_and_charges else self.doc.base_taxable_total
		else:
			self.doc.taxes_and_charges_added = self.doc.taxes_and_charges_deducted = 0.0
			for tax in self.doc.get("taxes"):
				if tax.category in ["Valuation and Total", "Total"]:
					if tax.add_deduct_tax == "Add":
						self.doc.taxes_and_charges_added += flt(tax.tax_amount_after_discount_amount)
					else:
						self.doc.taxes_and_charges_deducted += flt(tax.tax_amount_after_discount_amount)
			if self.should_round_transaction_currency():
				self.doc.round_floats_in(self.doc, ["taxes_and_charges_added", "taxes_and_charges_deducted"])

			self.doc.base_total_after_taxes = flt(self.doc.total_after_taxes * self.doc.conversion_rate) \
				if (self.doc.taxes_and_charges_added or self.doc.taxes_and_charges_deducted) \
				else self.doc.base_taxable_total

			self._set_in_company_currency(self.doc, ["taxes_and_charges_added", "taxes_and_charges_deducted"],
				not self.should_round_transaction_currency())

		self.doc.grand_total = self.doc.total_after_taxes - self.doc.total_discount_after_taxes
		self.doc.base_grand_total = flt(self.doc.grand_total * self.doc.conversion_rate)

		if self.should_round_transaction_currency():
			self.doc.round_floats_in(self.doc, ["grand_total", "total_after_taxes"])
		self.doc.round_floats_in(self.doc, ["base_grand_total", "base_total_after_taxes"])

		self.set_rounded_total()

	def calculate_total_net_weight(self):
		if self.doc.meta.get_field('total_net_weight'):
			self.doc.total_net_weight = 0.0
			for d in self.doc.items:
				if d.total_weight:
					self.doc.total_net_weight += d.total_weight

	def set_rounded_total(self):
		if self.doc.meta.get_field("rounded_total"):
			if self.doc.is_rounded_total_disabled():
				self.doc.rounded_total = self.doc.base_rounded_total = 0
				return

			self.doc.rounded_total = round_based_on_smallest_currency_fraction(self.doc.grand_total,
				self.doc.currency, self.doc.precision("rounded_total"))

			#if print_in_rate is set, we would have already calculated rounding adjustment
			self.doc.rounding_adjustment += flt(self.doc.rounded_total - self.doc.grand_total,
				self.doc.precision("rounding_adjustment"))

			self._set_in_company_currency(self.doc, ["rounding_adjustment", "rounded_total"])

	def _cleanup(self):
		for tax in self.doc.get("taxes"):
			tax.item_wise_tax_detail = json.dumps(tax.item_wise_tax_detail, separators=(',', ':'))
		for item in self.doc.get("items"):
			item.item_tax_detail = json.dumps(item.item_tax_detail, separators=(',', ':'))
			if not self.discount_amount_applied:
				item.item_tax_detail_before_discount = item.item_tax_detail

	def set_discount_amount(self):
		if self.doc.additional_discount_percentage:
			self.doc.discount_amount = flt(flt(self.doc.get(scrub(self.doc.apply_discount_on)))
				* self.doc.additional_discount_percentage / 100, self.doc.precision("discount_amount"))

	def apply_discount_amount(self):
		if self.doc.discount_amount:
			if not self.doc.apply_discount_on:
				frappe.throw(_("Please select Apply Discount On"))

			self.doc.base_discount_amount = flt(self.doc.discount_amount * self.doc.conversion_rate,
				self.doc.precision("base_discount_amount"))

			total_for_discount_amount = self.get_total_for_discount_amount()
			taxes = self.doc.get("taxes")
			net_total = 0

			if total_for_discount_amount:
				# calculate item amount after Discount Amount
				for i, item in enumerate(self.doc.get("items")):
					net_or_inclusive = self.get_item_amount_for_discount_amount(item)

					distributed_amount = flt(self.doc.discount_amount) * \
						net_or_inclusive / total_for_discount_amount

					item.net_amount = flt(item.net_amount - distributed_amount, item.precision("net_amount"))
					net_total += item.net_amount

					# discount amount rounding loss adjustment if no taxes
					if (self.doc.apply_discount_on == "Net Total" or not taxes or total_for_discount_amount==self.doc.net_total) \
						and i == len(self.doc.get("items")) - 1:
							discount_amount_loss = flt(self.doc.net_total - net_total - self.doc.discount_amount,
								self.doc.precision("net_total"))

							item.net_amount = flt(item.net_amount + discount_amount_loss,
								item.precision("net_amount"))

					item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate")) if item.qty else 0

					if not cint(item.apply_discount_after_taxes):
						item.taxable_amount = item.net_amount
						item.taxable_rate = item.net_rate

					self._set_in_company_currency(item, ["net_rate", "net_amount", "taxable_rate", "taxable_amount"])

				self.discount_amount_applied = True
				self._calculate()
		else:
			self.doc.base_discount_amount = 0

	def get_total_for_discount_amount(self):
		if self.doc.apply_discount_on == "Net Total":
			return self.doc.net_total
		else:
			actual_taxes_dict = {}

			for tax in self.doc.get("taxes"):
				if tax.charge_type in ["Actual", "Weighted Distribution", "Manual", "On Item Quantity"]:
					tax_amount = self.get_tax_amount_if_for_valuation_or_deduction(tax.tax_amount, tax)
					actual_taxes_dict.setdefault(tax.idx, tax_amount)
				elif tax.row_id in actual_taxes_dict:
					actual_tax_amount = flt(actual_taxes_dict.get(tax.row_id, 0)) * flt(tax.rate) / 100
					actual_taxes_dict.setdefault(tax.idx, actual_tax_amount)

			return flt(self.doc.grand_total - sum(actual_taxes_dict.values()),
				self.doc.precision("grand_total"))

	def get_item_amount_for_discount_amount(self, item):
		if self.doc.apply_discount_on == "Net Total" or not cint(item.apply_discount_after_taxes):
			return item.net_amount
		else:
			item_tax_detail = json.loads(item.item_tax_detail or '{}')
			actual_taxes_dict = {}

			for tax in self.doc.get("taxes"):
				if tax.charge_type in ["Actual", "Weighted Distribution", "Manual", "On Item Quantity"]:
					tax_amount = self.get_tax_amount_if_for_valuation_or_deduction(flt(item_tax_detail.get(tax.name)), tax)
					actual_taxes_dict.setdefault(tax.idx, tax_amount)
				elif tax.row_id in actual_taxes_dict:
					actual_tax_amount = flt(actual_taxes_dict.get(tax.row_id, 0)) * flt(tax.rate) / 100
					actual_taxes_dict.setdefault(tax.idx, actual_tax_amount)

			return flt(item.tax_inclusive_amount - sum(actual_taxes_dict.values()))


	def calculate_total_advance(self):
		if self.doc.docstatus < 2:
			total_allocated_amount = sum([flt(adv.allocated_amount, adv.precision("allocated_amount"))
				for adv in self.doc.get("advances")])

			self.doc.total_advance = flt(total_allocated_amount, self.doc.precision("total_advance"))

			grand_total = self.doc.rounded_total or self.doc.grand_total

			if self.doc.party_account_currency == self.doc.currency:
				invoice_total = flt(grand_total - flt(self.doc.write_off_amount),
					self.doc.precision("grand_total"))
			else:
				base_write_off_amount = flt(flt(self.doc.write_off_amount) * self.doc.conversion_rate,
					self.doc.precision("base_write_off_amount"))
				invoice_total = flt(grand_total * self.doc.conversion_rate,
					self.doc.precision("grand_total")) - base_write_off_amount

			if self.doc.docstatus == 0:
				if invoice_total > 0 and self.doc.total_advance > invoice_total:
					frappe.throw(_("Advance amount cannot be greater than {0} {1}")
						.format(self.doc.party_account_currency, invoice_total))

				self.calculate_outstanding_amount()

	def calculate_outstanding_amount(self):
		# NOTE:
		# write_off_amount is only for POS Invoice
		# total_advance is only for non POS Invoice
		if self.doc.doctype == "Sales Invoice":
			self.calculate_paid_amount()

		if self.doc.is_return and self.doc.return_against and not self.doc.get('is_pos'): return

		if self.should_round_transaction_currency():
			self.doc.round_floats_in(self.doc, ["grand_total", "total_advance", "write_off_amount"])
		self._set_in_company_currency(self.doc, ['write_off_amount'])

		if self.doc.doctype in ["Sales Invoice", "Purchase Invoice"]:
			grand_total = self.doc.rounded_total or self.doc.grand_total
			if self.doc.party_account_currency == self.doc.currency:
				total_amount_to_pay = flt(grand_total - self.doc.total_advance
					- flt(self.doc.write_off_amount), self.doc.precision("grand_total"))
			else:
				total_amount_to_pay = flt(flt(grand_total *
					self.doc.conversion_rate, self.doc.precision("grand_total")) - self.doc.total_advance
						- flt(self.doc.base_write_off_amount), self.doc.precision("grand_total"))

			self.doc.round_floats_in(self.doc, ["paid_amount"])
			change_amount = 0

			if self.doc.doctype == "Sales Invoice" and not self.doc.get('is_return'):
				self.calculate_write_off_amount()
				self.calculate_change_amount()
				change_amount = self.doc.change_amount \
					if self.doc.party_account_currency == self.doc.currency else self.doc.base_change_amount

			paid_amount = self.doc.paid_amount \
				if self.doc.party_account_currency == self.doc.currency else self.doc.base_paid_amount

			self.doc.outstanding_amount = flt(total_amount_to_pay - flt(paid_amount) + flt(change_amount),
				self.doc.precision("outstanding_amount"))

			if self.doc.doctype == 'Sales Invoice' and self.doc.get('is_pos') and self.doc.get('is_return'):
			 	self.update_paid_amount_for_return(total_amount_to_pay)

	def calculate_paid_amount(self):

		paid_amount = base_paid_amount = 0.0

		if self.doc.is_pos:
			for payment in self.doc.get('payments'):
				payment.amount = flt(payment.amount)
				payment.base_amount = payment.amount * flt(self.doc.conversion_rate)
				paid_amount += payment.amount
				base_paid_amount += payment.base_amount
		elif not self.doc.is_return:
			self.doc.set('payments', [])

		if self.doc.redeem_loyalty_points and self.doc.loyalty_amount:
			base_paid_amount += self.doc.loyalty_amount
			paid_amount += (self.doc.loyalty_amount / flt(self.doc.conversion_rate))

		self.doc.paid_amount = flt(paid_amount, self.doc.precision("paid_amount"))
		self.doc.base_paid_amount = flt(base_paid_amount, self.doc.precision("base_paid_amount"))

	def calculate_change_amount(self):
		self.doc.change_amount = 0.0
		self.doc.base_change_amount = 0.0

		grand_total = self.doc.rounded_total or self.doc.grand_total
		base_grand_total = self.doc.base_rounded_total or self.doc.base_grand_total

		if self.doc.doctype == "Sales Invoice" \
			and self.doc.paid_amount > grand_total and not self.doc.is_return \
			and any([d.type == "Cash" for d in self.doc.payments]):

			self.doc.change_amount = flt(self.doc.paid_amount - grand_total +
				self.doc.write_off_amount, self.doc.precision("change_amount"))

			self.doc.base_change_amount = flt(self.doc.base_paid_amount - base_grand_total +
				self.doc.base_write_off_amount, self.doc.precision("base_change_amount"))

	def calculate_write_off_amount(self):
		if flt(self.doc.change_amount) > 0:
			grand_total = self.doc.rounded_total or self.doc.grand_total

			self.doc.write_off_amount = flt(grand_total - self.doc.paid_amount
				+ self.doc.change_amount, self.doc.precision("write_off_amount"))
			self.doc.base_write_off_amount = flt(self.doc.write_off_amount * self.doc.conversion_rate,
				self.doc.precision("base_write_off_amount"))

	def calculate_margin(self, item):

		rate_with_margin = 0.0
		base_rate_with_margin = 0.0
		if flt(item.price_list_rate):
			if item.pricing_rules and not self.doc.ignore_pricing_rule:
				for d in get_applied_pricing_rules(item.pricing_rules):
					pricing_rule = frappe.get_cached_doc('Pricing Rule', d)

					if (pricing_rule.margin_type == 'Amount' and pricing_rule.currency == self.doc.currency)\
							or (pricing_rule.margin_type == 'Percentage'):
						item.margin_type = pricing_rule.margin_type
						item.margin_rate_or_amount = pricing_rule.margin_rate_or_amount
					else:
						item.margin_type = None
						item.margin_rate_or_amount = 0.0

			if item.margin_type and flt(item.rate) > flt(item.price_list_rate):
				margin_amount = flt(item.rate) - flt(item.price_list_rate)
				if item.margin_type == "Amount":
					item.margin_rate_or_amount = margin_amount
				elif item.margin_type == "Percentage":
					item.margin_rate_or_amount = margin_amount / flt(item.price_list_rate) * 100

			if item.margin_type and item.margin_rate_or_amount:
				margin_value = item.margin_rate_or_amount if item.margin_type == 'Amount' else flt(item.price_list_rate) * flt(item.margin_rate_or_amount) / 100
				rate_with_margin = flt(item.price_list_rate) + flt(margin_value)
				base_rate_with_margin = flt(rate_with_margin) * flt(self.doc.conversion_rate)

		return rate_with_margin, base_rate_with_margin

	def set_item_wise_tax_breakup(self):
		self.doc.other_charges_calculation = get_itemised_tax_breakup_html(self.doc)

	def update_paid_amount_for_return(self, total_amount_to_pay):
		default_mode_of_payment = frappe.db.get_value('Sales Invoice Payment',
			{'parent': self.doc.pos_profile, 'default': 1},
			['mode_of_payment', 'type', 'account'], as_dict=1)

		self.doc.payments = []

		if default_mode_of_payment:
			self.doc.append('payments', {
				'mode_of_payment': default_mode_of_payment.mode_of_payment,
				'type': default_mode_of_payment.type,
				'account': default_mode_of_payment.account,
				'amount': total_amount_to_pay
			})
		else:
			self.doc.is_pos = 0
			self.doc.pos_profile = ''

		self.calculate_paid_amount()


def get_itemised_tax_breakup_html(doc):
	if not doc.taxes:
		return
	frappe.flags.company = doc.company

	# get headers
	tax_accounts = []
	for tax in doc.taxes:
		if getattr(tax, "category", None) and tax.category=="Valuation":
			continue
		if tax.description not in tax_accounts:
			tax_accounts.append(tax.description)

	headers = get_itemised_tax_breakup_header(doc.doctype + " Item", tax_accounts)

	# get tax breakup data
	itemised_tax, itemised_taxable_amount, itemised_net_amount, itemised_qty = get_itemised_tax_breakup_data(doc)

	# currency
	if cint(doc.get("calculate_tax_on_company_currency")):
		currency = erpnext.get_company_currency(doc.company)
		conversion_rate = 1.0
		for k in itemised_taxable_amount.keys():
			itemised_taxable_amount[k] = itemised_taxable_amount[k] * doc.conversion_rate
		for k in itemised_net_amount.keys():
			itemised_net_amount[k] = itemised_net_amount[k] * doc.conversion_rate
	else:
		currency = doc.currency
		conversion_rate = doc.conversion_rate

	# get totals
	item_totals = {}
	tax_totals = {}
	total_taxes_and_charges = 0
	for item, taxes in iteritems(itemised_tax):
		item_totals.setdefault(item, itemised_net_amount[item])

		for tax, tax_data in iteritems(taxes):
			tax_totals.setdefault(tax, 0)

			tax_totals[tax] += tax_data.tax_amount
			item_totals[item] += tax_data.tax_amount
			total_taxes_and_charges += tax_data.tax_amount

	get_rounded_tax_amount(itemised_tax, doc.precision("tax_amount", "taxes"))

	update_itemised_tax_data(doc)
	frappe.flags.company = None

	return frappe.render_template(
		"templates/includes/itemised_tax_breakup.html", dict(
			headers=headers,
			itemised_tax=itemised_tax,
			itemised_taxable_amount=itemised_taxable_amount,
			itemised_net_amount=itemised_net_amount,
			itemised_qty=itemised_qty,
			tax_accounts=tax_accounts,
			item_totals=item_totals,
			tax_totals=tax_totals,
			total_taxes_and_charges=total_taxes_and_charges,
			conversion_rate=conversion_rate,
			currency=currency,
			doc=doc
		)
	)


@erpnext.allow_regional
def update_itemised_tax_data(doc):
	#Don't delete this method, used for localization
	pass

@erpnext.allow_regional
def get_itemised_tax_breakup_header(item_doctype, tax_accounts):
	out = [_("Item"), _("Net Amount")] + tax_accounts
	if item_doctype.startswith("Purchase"):
		out.append("Valuation Rate")
	return out

@erpnext.allow_regional
def get_itemised_tax_breakup_data(doc):
	itemised_tax = get_itemised_tax(doc.taxes)

	itemised_taxable_amount = get_itemised_taxable_amount(doc.items)

	itemised_net_amount = get_itemised_net_amount(doc.items)

	itemised_qty = get_itemised_qty(doc.items)

	return itemised_tax, itemised_taxable_amount, itemised_net_amount, itemised_qty

def get_itemised_tax(taxes, with_tax_account=False):
	itemised_tax = {}
	for tax in taxes:
		if getattr(tax, "category", None) and tax.category=="Valuation":
			continue

		item_tax_map = json.loads(tax.item_wise_tax_detail) if tax.item_wise_tax_detail else {}
		if item_tax_map:
			for item_code, tax_data in item_tax_map.items():
				itemised_tax.setdefault(item_code, frappe._dict())
				itemised_tax[item_code].setdefault(tax.description, frappe._dict(dict(
					tax_rate=0,
					tax_amount=0
				)))

				tax_rate = 0.0
				tax_amount = 0.0

				if isinstance(tax_data, list):
					tax_rate = flt(tax_data[0])
					tax_amount = flt(tax_data[1])
				else:
					tax_rate = flt(tax_data)

				itemised_tax[item_code][tax.description].tax_rate = tax_rate
				itemised_tax[item_code][tax.description].tax_amount += tax_amount

				if with_tax_account:
					itemised_tax[item_code][tax.description].tax_account = tax.account_head

	return itemised_tax

def get_itemised_taxable_amount(items):
	itemised_taxable_amount = frappe._dict()
	for item in items:
		item_code = item.item_code or item.item_name
		itemised_taxable_amount.setdefault(item_code, 0)
		itemised_taxable_amount[item_code] += item.taxable_amount

	return itemised_taxable_amount

def get_itemised_net_amount(items):
	itemised_net_amount = frappe._dict()
	for item in items:
		item_code = item.item_code or item.item_name
		itemised_net_amount.setdefault(item_code, 0)
		itemised_net_amount[item_code] += item.net_amount

	return itemised_net_amount

def get_itemised_qty(items):
	itemised_qty = frappe._dict()
	for item in items:
		item_code = item.item_code or item.item_name
		itemised_qty.setdefault(item_code, 0)
		itemised_qty[item_code] += item.qty

	return itemised_qty

def get_rounded_tax_amount(itemised_tax, precision):
	# Rounding based on tax_amount precision
	for taxes in itemised_tax.values():
		for tax_account in taxes:
			taxes[tax_account]["tax_amount"] = flt(taxes[tax_account]["tax_amount"], precision)
