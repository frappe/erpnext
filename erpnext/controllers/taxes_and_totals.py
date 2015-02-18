# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import json
from frappe import _, throw
from frappe.utils import cint, flt, rounded
from erpnext.setup.utils import get_company_currency
from erpnext.controllers.accounts_controller import validate_conversion_rate

class calculate_taxes_and_totals(object):
	def __init__(self, doc):
		self.doc = doc

		self.calculate()

	def calculate(self):
		self.discount_amount_applied = False
		self._calculate()

		if self.doc.meta.get_field("discount_amount"):
			self.apply_discount_amount()

		if self.doc.doctype in ["Sales Invoice", "Purchase Invoice"]:
			self.calculate_total_advance()

	def _calculate(self):
		# validate conversion rate
		company_currency = get_company_currency(self.doc.company)
		if not self.doc.currency or self.doc.currency == company_currency:
			self.doc.currency = company_currency
			self.doc.conversion_rate = 1.0
		else:
			validate_conversion_rate(self.doc.currency, self.doc.conversion_rate,
				self.doc.meta.get_label("conversion_rate"), self.doc.company)

		self.doc.conversion_rate = flt(self.doc.conversion_rate)

		self.calculate_item_values()
		self.initialize_taxes()

		if self.doc.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
			self.determine_exclusive_rate()

		self.calculate_net_total()
		self.calculate_taxes()
		self.calculate_totals()
		self._cleanup()

	def calculate_item_values(self):
		if not self.discount_amount_applied:
			for item in self.doc.get("items"):
				self.doc.round_floats_in(item)

				if item.discount_percentage == 100:
					item.rate = 0.0
				elif not item.rate:
					item.rate = flt(item.price_list_rate * (1.0 - (item.discount_percentage / 100.0)),
						self.doc.precision("rate", item))

				item.amount = flt(item.rate * item.qty,	self.doc.precision("amount", item))
				item.item_tax_amount = 0.0;

				self._set_in_company_currency(item, "price_list_rate", "base_price_list_rate")
				self._set_in_company_currency(item, "rate", "base_rate")
				self._set_in_company_currency(item, "amount", "base_amount")

	def _set_in_company_currency(self, item, print_field, base_field):
		"""set values in base currency"""
		value_in_company_currency = flt(self.doc.conversion_rate *
			flt(item.get(print_field), self.doc.precision(print_field, item)), self.doc.precision(base_field, item))
		item.set(base_field, value_in_company_currency)

	def initialize_taxes(self):
		for tax in self.doc.get("taxes"):
			tax.item_wise_tax_detail = {}
			tax_fields = ["total", "tax_amount_after_discount_amount",
				"tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"]

			if not self.discount_amount_applied:
				tax_fields.append("tax_amount")

			for fieldname in tax_fields:
				tax.set(fieldname, 0.0)

			self.validate_on_previous_row(tax)
			self.validate_inclusive_tax(tax)
			self.doc.round_floats_in(tax)

	def validate_on_previous_row(self, tax):
		"""
			validate if a valid row id is mentioned in case of
			On Previous Row Amount and On Previous Row Total
		"""
		if tax.charge_type in ["On Previous Row Amount", "On Previous Row Total"] and \
				(not tax.row_id or cint(tax.row_id) >= tax.idx):
			throw(_("Please specify a valid Row ID for {0} in row {1}").format(_(tax.doctype), tax.idx))

	def validate_inclusive_tax(self, tax):
		def _on_previous_row_error(row_range):
			throw(_("To include tax in row {0} in Item rate, taxes in rows {1} must also be included").format(tax.idx,
				row_range))

		if cint(getattr(tax, "included_in_print_rate", None)):
			if tax.charge_type == "Actual":
				# inclusive tax cannot be of type Actual
				throw(_("Charge of type 'Actual' in row {0} cannot be included in Item Rate").format(tax.idx))
			elif tax.charge_type == "On Previous Row Amount" and \
					not cint(self.doc.get("taxes")[cint(tax.row_id) - 1].included_in_print_rate):
				# referred row should also be inclusive
				_on_previous_row_error(tax.row_id)
			elif tax.charge_type == "On Previous Row Total" and \
					not all([cint(t.included_in_print_rate) for t in self.doc.get("taxes")[:cint(tax.row_id) - 1]]):
				# all rows about the reffered tax should be inclusive
				_on_previous_row_error("1 - %d" % (tax.row_id,))

	def determine_exclusive_rate(self):
		if not any((cint(tax.included_in_print_rate) for tax in self.doc.get("taxes"))):
			# no inclusive tax
			return

		for item in self.doc.get("items"):
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
			cumulated_tax_fraction = 0
			for i, tax in enumerate(self.doc.get("taxes")):
				tax.tax_fraction_for_current_item = self.get_current_tax_fraction(tax, item_tax_map)

				if i==0:
					tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item
				else:
					tax.grand_total_fraction_for_current_item = \
						self.doc.get("taxes")[i-1].grand_total_fraction_for_current_item \
						+ tax.tax_fraction_for_current_item

				cumulated_tax_fraction += tax.tax_fraction_for_current_item

			if cumulated_tax_fraction and not self.discount_amount_applied and item.qty:
				item.base_amount = flt((item.amount * self.doc.conversion_rate) /
					(1 + cumulated_tax_fraction), self.doc.precision("base_amount", item))

				item.base_rate = flt(item.base_amount / item.qty, self.doc.precision("base_rate", item))
				item.discount_percentage = flt(item.discount_percentage, self.doc.precision("discount_percentage", item))

				if item.discount_percentage == 100:
					item.base_price_list_rate = item.base_rate
					item.base_rate = 0.0
				else:
					item.base_price_list_rate = flt(item.base_rate / (1 - (item.discount_percentage / 100.0)),
						self.doc.precision("base_price_list_rate", item))

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

		return current_tax_fraction

	def _get_tax_rate(self, tax, item_tax_map):
		if item_tax_map.has_key(tax.account_head):
			return flt(item_tax_map.get(tax.account_head), self.doc.precision("rate", tax))
		else:
			return tax.rate

	def calculate_net_total(self):
		self.doc.base_net_total = self.doc.net_total = 0.0

		for item in self.doc.get("items"):
			self.doc.base_net_total += item.base_amount
			self.doc.net_total += item.amount

		self.doc.round_floats_in(self.doc, ["base_net_total", "net_total"])

	def calculate_taxes(self):
		# maintain actual tax rate based on idx
		actual_tax_dict = dict([[tax.idx, flt(tax.rate, self.doc.precision("tax_amount", tax))]
			for tax in self.doc.get("taxes") if tax.charge_type == "Actual"])

		for n, item in enumerate(self.doc.get("items")):
			item_tax_map = self._load_item_tax_rate(item.item_tax_rate)

			for i, tax in enumerate(self.doc.get("taxes")):
				# tax_amount represents the amount of tax for the current step
				current_tax_amount = self.get_current_tax_amount(item, tax, item_tax_map)

				# Adjust divisional loss to the last item
				if tax.charge_type == "Actual":
					actual_tax_dict[tax.idx] -= current_tax_amount
					if n == len(self.doc.get("items")) - 1:
						current_tax_amount += actual_tax_dict[tax.idx]

				# store tax_amount for current item as it will be used for
				# charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount

				# accumulate tax amount into tax.tax_amount
				if not self.discount_amount_applied:
					tax.tax_amount += current_tax_amount

				tax.tax_amount_after_discount_amount += current_tax_amount

				if getattr(tax, "category", None):
					# if just for valuation, do not add the tax amount in total
					# hence, setting it as 0 for further steps
					current_tax_amount = 0.0 if (tax.category == "Valuation") \
						else current_tax_amount

					current_tax_amount *= -1.0 if (tax.add_deduct_tax == "Deduct") else 1.0

				# Calculate tax.total viz. grand total till that step
				# note: grand_total_for_current_item contains the contribution of
				# item's amount, previously applied tax and the current tax on that item
				if i==0:
					tax.grand_total_for_current_item = flt(item.base_amount + current_tax_amount,
						self.doc.precision("total", tax))
				else:
					tax.grand_total_for_current_item = \
						flt(self.doc.get("taxes")[i-1].grand_total_for_current_item +
							current_tax_amount, self.doc.precision("total", tax))

				# in tax.total, accumulate grand total of each item
				tax.total += tax.grand_total_for_current_item

				# set precision in the last item iteration
				if n == len(self.doc.get("items")) - 1:
					self.round_off_totals(tax)

					# adjust Discount Amount loss in last tax iteration
					if i == (len(self.doc.get("taxes")) - 1) and self.discount_amount_applied:
						self.adjust_discount_amount_loss(tax)

	def get_current_tax_amount(self, item, tax, item_tax_map):
		tax_rate = self._get_tax_rate(tax, item_tax_map)
		current_tax_amount = 0.0

		if tax.charge_type == "Actual":
			# distribute the tax amount proportionally to each item row
			actual = flt(tax.rate, self.doc.precision("tax_amount", tax))
			current_tax_amount = (self.doc.base_net_total
				and ((item.base_amount / self.doc.base_net_total) * actual)
				or 0)
		elif tax.charge_type == "On Net Total":
			current_tax_amount = (tax_rate / 100.0) * item.base_amount
		elif tax.charge_type == "On Previous Row Amount":
			current_tax_amount = (tax_rate / 100.0) * \
				self.doc.get("taxes")[cint(tax.row_id) - 1].tax_amount_for_current_item
		elif tax.charge_type == "On Previous Row Total":
			current_tax_amount = (tax_rate / 100.0) * \
				self.doc.get("taxes")[cint(tax.row_id) - 1].grand_total_for_current_item

		current_tax_amount = flt(current_tax_amount, self.doc.precision("tax_amount", tax))

		# store tax breakup for each item
		key = item.item_code or item.item_name
		if tax.item_wise_tax_detail.get(key):
			item_wise_tax_amount = tax.item_wise_tax_detail[key][1] + current_tax_amount
			tax.item_wise_tax_detail[key] = [tax_rate,item_wise_tax_amount]
		else:
			tax.item_wise_tax_detail[key] = [tax_rate,current_tax_amount]

		return current_tax_amount

	def round_off_totals(self, tax):
		tax.total = flt(tax.total, self.doc.precision("total", tax))
		tax.tax_amount = flt(tax.tax_amount, self.doc.precision("tax_amount", tax))
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount,
			self.doc.precision("tax_amount", tax))

	def adjust_discount_amount_loss(self, tax):
		discount_amount_loss = self.doc.base_grand_total - flt(self.doc.base_discount_amount) - tax.total
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount +
			discount_amount_loss, self.doc.precision("tax_amount", tax))
		tax.total = flt(tax.total + discount_amount_loss, self.doc.precision("total", tax))

	def calculate_totals(self):
		self.doc.base_grand_total = flt(self.doc.get("taxes")[-1].total
			if self.doc.get("taxes") else self.doc.base_net_total)

		print self.doc
		self.doc.base_total_taxes_and_charges = flt(self.doc.base_grand_total - self.doc.base_net_total,
			self.doc.precision("base_total_taxes_and_charges"))

		if self.doc.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
			self.doc.grand_total = flt(self.doc.base_grand_total / self.doc.conversion_rate) \
				if (self.doc.base_total_taxes_and_charges or self.doc.discount_amount) else self.doc.net_total

			self.doc.total_taxes_and_charges = flt(self.doc.grand_total - self.doc.net_total +
				flt(self.doc.discount_amount), self.doc.precision("total_taxes_and_charges"))
		else:
			self.doc.base_taxes_and_charges_added, self.base_taxes_and_charges_deducted = 0.0, 0.0
			for tax in self.doc.get("taxes"):
				if tax.category in ["Valuation and Total", "Total"]:
					if tax.add_deduct_tax == "Add":
						self.doc.base_taxes_and_charges_added += flt(tax.tax_amount)
					else:
						self.doc.base_taxes_and_charges_deducted += flt(tax.tax_amount)

			self.doc.round_floats_in(self.doc, ["base_taxes_and_charges_added", "base_taxes_and_charges_deducted"])

			self.doc.grand_total = flt(self.doc.base_grand_total / self.doc.conversion_rate) \
				if (self.doc.base_taxes_and_charges_added or self.doc.base_taxes_and_charges_deducted) else self.doc.net_total

			self.doc.total_taxes_and_charges = flt(self.doc.grand_total - self.doc.net_total,
				self.doc.precision("total_taxes_and_charges"))

			self.doc.taxes_and_charges_added = flt(self.doc.base_taxes_and_charges_added / self.doc.conversion_rate,
				self.doc.precision("taxes_and_charges_added"))
			self.doc.taxes_and_charges_deducted = flt(self.doc.base_taxes_and_charges_deducted / self.doc.conversion_rate,
				self.doc.precision("taxes_and_charges_deducted"))

		self.doc.base_grand_total = flt(self.doc.base_grand_total, self.doc.precision("base_grand_total"))
		self.doc.grand_total = flt(self.doc.grand_total, self.doc.precision("grand_total"))

		if self.doc.meta.get_field("base_rounded_total"):
			self.doc.base_rounded_total = rounded(self.doc.base_grand_total)
		if self.doc.meta.get_field("rounded_total"):
			self.doc.rounded_total = rounded(self.doc.grand_total)

	def _cleanup(self):
		for tax in self.doc.get("taxes"):
			tax.item_wise_tax_detail = json.dumps(tax.item_wise_tax_detail, separators=(',', ':'))

	def apply_discount_amount(self):
		if self.doc.discount_amount:
			self.doc.base_discount_amount = flt(self.doc.discount_amount * self.doc.conversion_rate,
				self.doc.precision("base_discount_amount"))

			grand_total_for_discount_amount = self.get_grand_total_for_discount_amount()

			if grand_total_for_discount_amount:
				# calculate item amount after Discount Amount
				for item in self.doc.get("items"):
					distributed_amount = flt(self.doc.base_discount_amount) * item.base_amount / grand_total_for_discount_amount
					item.base_amount = flt(item.base_amount - distributed_amount, self.doc.precision("base_amount", item))

				self.discount_amount_applied = True
				self._calculate()
		else:
			self.doc.base_discount_amount = 0

	def get_grand_total_for_discount_amount(self):
		actual_taxes_dict = {}

		for tax in self.doc.get("taxes"):
			if tax.charge_type == "Actual":
				actual_taxes_dict.setdefault(tax.idx, tax.tax_amount)
			elif tax.row_id in actual_taxes_dict:
				actual_tax_amount = flt(actual_taxes_dict.get(tax.row_id, 0)) * flt(tax.rate) / 100
				actual_taxes_dict.setdefault(tax.idx, actual_tax_amount)

		grand_total_for_discount_amount = flt(self.doc.base_grand_total - sum(actual_taxes_dict.values()),
			self.doc.precision("base_grand_total"))
		return grand_total_for_discount_amount


	def calculate_total_advance(self, parenttype, advance_parentfield):
		if self.docstatus < 2:
			sum_of_allocated_amount = sum([flt(adv.allocated_amount, self.doc.precision("allocated_amount", adv))
				for adv in self.doc.get("advances")])

			self.doc.total_advance = flt(sum_of_allocated_amount, self.doc.precision("total_advance"))

			if self.docstatus == 0:
				self.calculate_outstanding_amount()

	def calculate_outstanding_amount(self):
		# NOTE:
		# write_off_amount is only for POS Invoice
		# total_advance is only for non POS Invoice

		if self.doc.doctype == "Sales Invoice":
			self.doc.round_floats_in(self.doc, ["base_grand_total", "total_advance", "write_off_amount", "paid_amount"])
			total_amount_to_pay = self.doc.base_grand_total - self.doc.write_off_amount
			self.doc.outstanding_amount = flt(total_amount_to_pay - self.doc.total_advance - self.doc.paid_amount,
				self.doc.precision("outstanding_amount"))
		else:
			self.doc.round_floats_in(self.doc, ["total_advance", "write_off_amount"])
			self.doc.total_amount_to_pay = flt(self.doc.base_grand_total - self.doc.write_off_amount,
				self.doc.precision("total_amount_to_pay"))
			self.doc.outstanding_amount = flt(self.doc.total_amount_to_pay - self.doc.total_advance,
				self.doc.precision("outstanding_amount"))
