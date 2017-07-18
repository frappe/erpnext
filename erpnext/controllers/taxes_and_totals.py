# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import json
import frappe, erpnext
from frappe import _, scrub
from frappe.utils import cint, flt, round_based_on_smallest_currency_fraction
from erpnext.controllers.accounts_controller import validate_conversion_rate, \
	validate_taxes_and_charges, validate_inclusive_tax

class calculate_taxes_and_totals(object):
	def __init__(self, doc):
		self.doc = doc
		self.calculate()

	def calculate(self):
		self.discount_amount_applied = False
		self._calculate()

		if self.doc.meta.get_field("discount_amount"):
			self.set_discount_amount()
			self.apply_discount_amount()

		if self.doc.doctype in ["Sales Invoice", "Purchase Invoice"]:
			self.calculate_total_advance()
			
		if self.doc.meta.get_field("other_charges_calculation"):
			self.set_item_wise_tax_breakup()

	def _calculate(self):
		self.calculate_item_values()
		self.initialize_taxes()
		self.determine_exclusive_rate()
		self.calculate_net_total()
		self.calculate_taxes()
		self.manipulate_grand_total_for_inclusive_tax()
		self.calculate_totals()
		self._cleanup()

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
				self.doc.round_floats_in(item)

				if item.discount_percentage == 100:
					item.rate = 0.0
				elif not item.rate:
					item.rate = flt(item.price_list_rate *
						(1.0 - (item.discount_percentage / 100.0)), item.precision("rate"))

				if item.doctype in ['Quotation Item', 'Sales Order Item', 'Delivery Note Item', 'Sales Invoice Item']:
					item.rate_with_margin = self.calculate_margin(item)

					item.rate = flt(item.rate_with_margin * (1.0 - (item.discount_percentage / 100.0)), item.precision("rate"))\
						if item.rate_with_margin > 0 else item.rate

				item.net_rate = item.rate
				item.amount = flt(item.rate * item.qty,	item.precision("amount"))
				item.net_amount = item.amount

				self._set_in_company_currency(item, ["price_list_rate", "rate", "net_rate", "amount", "net_amount"])

				item.item_tax_amount = 0.0

	def _set_in_company_currency(self, doc, fields):
		"""set values in base currency"""
		for f in fields:
			val = flt(flt(doc.get(f), doc.precision(f)) * self.doc.conversion_rate, doc.precision("base_" + f))
			doc.set("base_" + f, val)

	def initialize_taxes(self):
		for tax in self.doc.get("taxes"):
			if not self.discount_amount_applied:
				validate_taxes_and_charges(tax)
				validate_inclusive_tax(tax, self.doc)

			tax.item_wise_tax_detail = {}
			tax_fields = ["total", "tax_amount_after_discount_amount",
				"tax_amount_for_current_item", "grand_total_for_current_item",
				"tax_fraction_for_current_item", "grand_total_fraction_for_current_item"]

			if tax.charge_type != "Actual" and \
				not (self.discount_amount_applied and self.doc.apply_discount_on=="Grand Total"):
					tax_fields.append("tax_amount")

			for fieldname in tax_fields:
				tax.set(fieldname, 0.0)

			self.doc.round_floats_in(tax)

	def determine_exclusive_rate(self):
		if not any((cint(tax.included_in_print_rate) for tax in self.doc.get("taxes"))):
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
				item.net_amount = flt(item.amount / (1 + cumulated_tax_fraction), item.precision("net_amount"))
				item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate"))
				item.discount_percentage = flt(item.discount_percentage, item.precision("discount_percentage"))

				self._set_in_company_currency(item, ["net_rate", "net_amount"])

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
		if item_tax_map.has_key(tax.account_head):
			return flt(item_tax_map.get(tax.account_head), self.doc.precision("rate", tax))
		else:
			return tax.rate

	def calculate_net_total(self):
		self.doc.total = self.doc.base_total = self.doc.net_total = self.doc.base_net_total = 0.0

		for item in self.doc.get("items"):
			self.doc.total += item.amount
			self.doc.base_total += item.base_amount
			self.doc.net_total += item.net_amount
			self.doc.base_net_total += item.base_net_amount

		self.doc.round_floats_in(self.doc, ["total", "base_total", "net_total", "base_net_total"])

	def calculate_taxes(self):
		# maintain actual tax rate based on idx
		actual_tax_dict = dict([[tax.idx, flt(tax.tax_amount, tax.precision("tax_amount"))]
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

				# accumulate tax amount into tax.tax_amount
				if tax.charge_type != "Actual" and \
					not (self.discount_amount_applied and self.doc.apply_discount_on=="Grand Total"):
						tax.tax_amount += current_tax_amount

				# store tax_amount for current item as it will be used for
				# charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount

				# set tax after discount
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
					tax.grand_total_for_current_item = flt(item.net_amount + current_tax_amount, tax.precision("total"))
				else:
					tax.grand_total_for_current_item = \
						flt(self.doc.get("taxes")[i-1].grand_total_for_current_item + current_tax_amount, tax.precision("total"))

				# in tax.total, accumulate grand total of each item
				tax.total += tax.grand_total_for_current_item

				# set precision in the last item iteration
				if n == len(self.doc.get("items")) - 1:
					self.round_off_totals(tax)

					# adjust Discount Amount loss in last tax iteration
					if i == (len(self.doc.get("taxes")) - 1) and self.discount_amount_applied \
						and self.doc.discount_amount and self.doc.apply_discount_on == "Grand Total":
							self.adjust_discount_amount_loss(tax)



	def get_current_tax_amount(self, item, tax, item_tax_map):
		tax_rate = self._get_tax_rate(tax, item_tax_map)
		current_tax_amount = 0.0

		if tax.charge_type == "Actual":
			# distribute the tax amount proportionally to each item row
			actual = flt(tax.tax_amount, tax.precision("tax_amount"))
			current_tax_amount = item.net_amount*actual / self.doc.net_total if self.doc.net_total else 0.0

		elif tax.charge_type == "On Net Total":
			current_tax_amount = (tax_rate / 100.0) * item.net_amount
		elif tax.charge_type == "On Previous Row Amount":
			current_tax_amount = (tax_rate / 100.0) * \
				self.doc.get("taxes")[cint(tax.row_id) - 1].tax_amount_for_current_item
		elif tax.charge_type == "On Previous Row Total":
			current_tax_amount = (tax_rate / 100.0) * \
				self.doc.get("taxes")[cint(tax.row_id) - 1].grand_total_for_current_item

		current_tax_amount = flt(current_tax_amount, tax.precision("tax_amount"))

		self.set_item_wise_tax(item, tax, tax_rate, current_tax_amount)

		return current_tax_amount

	def set_item_wise_tax(self, item, tax, tax_rate, current_tax_amount):
		# store tax breakup for each item
		key = item.item_code or item.item_name
		item_wise_tax_amount = current_tax_amount*self.doc.conversion_rate
		if tax.item_wise_tax_detail.get(key):
			item_wise_tax_amount += tax.item_wise_tax_detail[key][1]

		tax.item_wise_tax_detail[key] = [tax_rate,flt(item_wise_tax_amount, tax.precision("base_tax_amount"))]

	def round_off_totals(self, tax):
		tax.total = flt(tax.total, tax.precision("total"))
		tax.tax_amount = flt(tax.tax_amount, tax.precision("tax_amount"))
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount, tax.precision("tax_amount"))

		self._set_in_company_currency(tax, ["total", "tax_amount", "tax_amount_after_discount_amount"])

	def adjust_discount_amount_loss(self, tax):
		discount_amount_loss = self.doc.grand_total - flt(self.doc.discount_amount) - tax.total
		tax.tax_amount_after_discount_amount = flt(tax.tax_amount_after_discount_amount +
			discount_amount_loss, tax.precision("tax_amount"))
		tax.total = flt(tax.total + discount_amount_loss, tax.precision("total"))

		self._set_in_company_currency(tax, ["total", "tax_amount_after_discount_amount"])

	def manipulate_grand_total_for_inclusive_tax(self):
		# if fully inclusive taxes and diff
		if self.doc.get("taxes") and all(cint(t.included_in_print_rate) for t in self.doc.get("taxes")):
			last_tax = self.doc.get("taxes")[-1]
			diff = self.doc.total - flt(last_tax.total, self.doc.precision("grand_total"))

			if diff and abs(diff) <= (2.0 / 10**last_tax.precision("tax_amount")):
				last_tax.tax_amount += diff
				last_tax.tax_amount_after_discount_amount += diff
				last_tax.total += diff

				self._set_in_company_currency(last_tax,
					["total", "tax_amount", "tax_amount_after_discount_amount"])

	def calculate_totals(self):
		self.doc.grand_total = flt(self.doc.get("taxes")[-1].total
			if self.doc.get("taxes") else self.doc.net_total)

		self.doc.total_taxes_and_charges = flt(self.doc.grand_total - self.doc.net_total,
			self.doc.precision("total_taxes_and_charges"))

		self._set_in_company_currency(self.doc, ["total_taxes_and_charges"])

		if self.doc.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
			self.doc.base_grand_total = flt(self.doc.grand_total * self.doc.conversion_rate) \
				if self.doc.total_taxes_and_charges else self.doc.base_net_total
		else:
			self.doc.taxes_and_charges_added = self.doc.taxes_and_charges_deducted = 0.0
			for tax in self.doc.get("taxes"):
				if tax.category in ["Valuation and Total", "Total"]:
					if tax.add_deduct_tax == "Add":
						self.doc.taxes_and_charges_added += flt(tax.tax_amount_after_discount_amount)
					else:
						self.doc.taxes_and_charges_deducted += flt(tax.tax_amount_after_discount_amount)

			self.doc.round_floats_in(self.doc, ["taxes_and_charges_added", "taxes_and_charges_deducted"])

			self.doc.base_grand_total = flt(self.doc.grand_total * self.doc.conversion_rate) \
				if (self.doc.taxes_and_charges_added or self.doc.taxes_and_charges_deducted) \
				else self.doc.base_net_total

			self._set_in_company_currency(self.doc, ["taxes_and_charges_added", "taxes_and_charges_deducted"])

		self.doc.round_floats_in(self.doc, ["grand_total", "base_grand_total"])

		if self.doc.meta.get_field("rounded_total"):
			self.doc.rounded_total = round_based_on_smallest_currency_fraction(self.doc.grand_total,
				self.doc.currency, self.doc.precision("rounded_total"))
		if self.doc.meta.get_field("base_rounded_total"):
			company_currency = erpnext.get_company_currency(self.doc.company)

			self.doc.base_rounded_total = \
				round_based_on_smallest_currency_fraction(self.doc.base_grand_total,
					company_currency, self.doc.precision("base_rounded_total"))

	def _cleanup(self):
		for tax in self.doc.get("taxes"):
			tax.item_wise_tax_detail = json.dumps(tax.item_wise_tax_detail, separators=(',', ':'))

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
					distributed_amount = flt(self.doc.discount_amount) * \
						item.net_amount / total_for_discount_amount

					item.net_amount = flt(item.net_amount - distributed_amount, item.precision("net_amount"))
					net_total += item.net_amount

					# discount amount rounding loss adjustment if no taxes
					if (not taxes or self.doc.apply_discount_on == "Net Total") \
						and i == len(self.doc.get("items")) - 1:
							discount_amount_loss = flt(self.doc.net_total - net_total - self.doc.discount_amount,
								self.doc.precision("net_total"))

							item.net_amount = flt(item.net_amount + discount_amount_loss,
								item.precision("net_amount"))

					item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate")) if item.qty else 0

					self._set_in_company_currency(item, ["net_rate", "net_amount"])

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
				if tax.charge_type == "Actual":
					actual_taxes_dict.setdefault(tax.idx, tax.tax_amount)
				elif tax.row_id in actual_taxes_dict:
					actual_tax_amount = flt(actual_taxes_dict.get(tax.row_id, 0)) * flt(tax.rate) / 100
					actual_taxes_dict.setdefault(tax.idx, actual_tax_amount)

			return flt(self.doc.grand_total - sum(actual_taxes_dict.values()), self.doc.precision("grand_total"))


	def calculate_total_advance(self):
		if self.doc.docstatus < 2:
			total_allocated_amount = sum([flt(adv.allocated_amount, adv.precision("allocated_amount"))
				for adv in self.doc.get("advances")])

			self.doc.total_advance = flt(total_allocated_amount, self.doc.precision("total_advance"))

			if self.doc.party_account_currency == self.doc.currency:
				invoice_total = flt(self.doc.grand_total - flt(self.doc.write_off_amount), 
					self.doc.precision("grand_total"))
			else:
				base_write_off_amount = flt(flt(self.doc.write_off_amount) * self.doc.conversion_rate, 
					self.doc.precision("base_write_off_amount"))
				invoice_total = flt(self.doc.grand_total * self.doc.conversion_rate, 
					self.doc.precision("grand_total")) - base_write_off_amount
				
			if invoice_total > 0 and self.doc.total_advance > invoice_total:
				frappe.throw(_("Advance amount cannot be greater than {0} {1}")
					.format(self.doc.party_account_currency, invoice_total))

			if self.doc.docstatus == 0:
				self.calculate_outstanding_amount()

	def calculate_outstanding_amount(self):
		# NOTE:
		# write_off_amount is only for POS Invoice
		# total_advance is only for non POS Invoice
		if self.doc.doctype == "Sales Invoice":
			self.calculate_paid_amount()

		if self.doc.is_return: return

		self.doc.round_floats_in(self.doc, ["grand_total", "total_advance", "write_off_amount"])
		self._set_in_company_currency(self.doc, ['write_off_amount'])

		if self.doc.party_account_currency == self.doc.currency:
			total_amount_to_pay = flt(self.doc.grand_total  - self.doc.total_advance
				- flt(self.doc.write_off_amount), self.doc.precision("grand_total"))
		else:
			total_amount_to_pay = flt(flt(self.doc.grand_total *
				self.doc.conversion_rate, self.doc.precision("grand_total")) - self.doc.total_advance
					- flt(self.doc.base_write_off_amount), self.doc.precision("grand_total"))

		if self.doc.doctype == "Sales Invoice":			
			self.doc.round_floats_in(self.doc, ["paid_amount"])
			self.calculate_write_off_amount()
			self.calculate_change_amount()
			
			paid_amount = self.doc.paid_amount \
				if self.doc.party_account_currency == self.doc.currency else self.doc.base_paid_amount
			
			change_amount = self.doc.change_amount \
				if self.doc.party_account_currency == self.doc.currency else self.doc.base_change_amount

			self.doc.outstanding_amount = flt(total_amount_to_pay - flt(paid_amount) +
				flt(change_amount), self.doc.precision("outstanding_amount"))

		elif self.doc.doctype == "Purchase Invoice":
			self.doc.outstanding_amount = flt(total_amount_to_pay, self.doc.precision("outstanding_amount"))

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

		self.doc.paid_amount = flt(paid_amount, self.doc.precision("paid_amount"))
		self.doc.base_paid_amount = flt(base_paid_amount, self.doc.precision("base_paid_amount"))

	def calculate_change_amount(self):
		self.doc.change_amount = 0.0
		self.doc.base_change_amount = 0.0
		if self.doc.paid_amount > self.doc.grand_total and not self.doc.is_return \
			and any([d.type == "Cash" for d in self.doc.payments]):

			self.doc.change_amount = flt(self.doc.paid_amount - self.doc.grand_total +
				self.doc.write_off_amount, self.doc.precision("change_amount"))

			self.doc.base_change_amount = flt(self.doc.base_paid_amount - self.doc.base_grand_total +
				self.doc.base_write_off_amount, self.doc.precision("base_change_amount"))

	def calculate_write_off_amount(self):
		if flt(self.doc.change_amount) > 0:
			self.doc.write_off_amount = flt(self.doc.grand_total - self.doc.paid_amount + self.doc.change_amount,
				self.doc.precision("write_off_amount"))
			self.doc.base_write_off_amount = flt(self.doc.write_off_amount * self.doc.conversion_rate,
				self.doc.precision("base_write_off_amount"))

	def calculate_margin(self, item):
		rate_with_margin = 0.0
		if item.price_list_rate:
			if item.pricing_rule and not self.doc.ignore_pricing_rule:
				pricing_rule = frappe.get_doc('Pricing Rule', item.pricing_rule)
				item.margin_type = pricing_rule.margin_type
				item.margin_rate_or_amount = pricing_rule.margin_rate_or_amount

			if item.margin_type and item.margin_rate_or_amount:
				margin_value = item.margin_rate_or_amount if item.margin_type == 'Amount' else flt(item.price_list_rate) * flt(item.margin_rate_or_amount) / 100
				rate_with_margin = flt(item.price_list_rate) + flt(margin_value)

		return rate_with_margin

	def set_item_wise_tax_breakup(self):
		if not self.doc.taxes:
			return
		frappe.flags.company = self.doc.company
		
		# get headers
		tax_accounts = list(set([d.description for d in self.doc.taxes]))
		headers = get_itemised_tax_breakup_header(self.doc.doctype + " Item", tax_accounts)
		
		# get tax breakup data
		itemised_tax, itemised_taxable_amount = get_itemised_tax_breakup_data(self.doc)
		
		frappe.flags.company = None
		
		self.doc.other_charges_calculation = frappe.render_template(
			"templates/includes/itemised_tax_breakup.html", dict(
				headers=headers,
				itemised_tax=itemised_tax,
				itemised_taxable_amount=itemised_taxable_amount,
				tax_accounts=tax_accounts,
				company_currency=erpnext.get_company_currency(self.doc.company)
			)
		)

@erpnext.allow_regional
def get_itemised_tax_breakup_header(item_doctype, tax_accounts):
	return [_("Item"), _("Taxable Amount")] + tax_accounts

@erpnext.allow_regional
def get_itemised_tax_breakup_data(doc):
	itemised_tax = get_itemised_tax(doc.taxes)

	itemised_taxable_amount = get_itemised_taxable_amount(doc.items)

	return itemised_tax, itemised_taxable_amount

def get_itemised_tax(taxes):
	itemised_tax = {}
	for tax in taxes:
		tax_amount_precision = tax.precision("tax_amount")
		tax_rate_precision = tax.precision("rate")
		
		item_tax_map = json.loads(tax.item_wise_tax_detail) if tax.item_wise_tax_detail else {}
		
		for item_code, tax_data in item_tax_map.items():
			itemised_tax.setdefault(item_code, frappe._dict())
			
			if isinstance(tax_data, list) and tax_data[0]:
				precision = tax_amount_precision if tax.charge_type == "Actual" else tax_rate_precision
				
				itemised_tax[item_code][tax.description] = frappe._dict(dict(
					tax_rate=flt(tax_data[0], precision),
					tax_amount=flt(tax_data[1], tax_amount_precision)
				))
			else:
				itemised_tax[item_code][tax.description] = frappe._dict(dict(
					tax_rate=flt(tax_data, tax_rate_precision),
					tax_amount=0.0
				))

	return itemised_tax

def get_itemised_taxable_amount(items):
	itemised_taxable_amount = frappe._dict()
	for item in items:
		item_code = item.item_code or item.item_name
		itemised_taxable_amount.setdefault(item_code, 0)
		itemised_taxable_amount[item_code] += item.net_amount

	return itemised_taxable_amount