# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, msgprint, throw
from frappe.model.document import Document
from frappe.utils import flt, fmt_money

import erpnext


class OverlappingConditionError(frappe.ValidationError): pass
class FromGreaterThanToError(frappe.ValidationError): pass
class ManyBlankToValuesError(frappe.ValidationError): pass

class ShippingRule(Document):
	def validate(self):
		self.validate_from_to_values()
		self.sort_shipping_rule_conditions()
		self.validate_overlapping_shipping_rule_conditions()

	def validate_from_to_values(self):
		zero_to_values = []

		for d in self.get("conditions"):
			self.round_floats_in(d)

			# values cannot be negative
			self.validate_value("from_value", ">=", 0.0, d)
			self.validate_value("to_value", ">=", 0.0, d)

			if not d.to_value:
				zero_to_values.append(d)
			elif d.from_value >= d.to_value:
				throw(_("From value must be less than to value in row {0}").format(d.idx), FromGreaterThanToError)

		# check if more than two or more rows has To Value = 0
		if len(zero_to_values) >= 2:
			throw(_('There can only be one Shipping Rule Condition with 0 or blank value for "To Value"'),
				ManyBlankToValuesError)

	def apply(self, doc):
		'''Apply shipping rule on given doc. Called from accounts controller'''

		shipping_amount = 0.0
		by_value = False

		if doc.get_shipping_address():
			# validate country only if there is address
			self.validate_countries(doc)

		if self.calculate_based_on == 'Net Total':
			value = doc.base_net_total
			by_value = True

		elif self.calculate_based_on == 'Net Weight':
			value = doc.total_net_weight
			by_value = True

		elif self.calculate_based_on == 'Fixed':
			shipping_amount = self.shipping_amount

		# shipping amount by value, apply conditions
		if by_value:
			shipping_amount = self.get_shipping_amount_from_rules(value)

		# convert to order currency
		if doc.currency != doc.company_currency:
			shipping_amount = flt(shipping_amount / doc.conversion_rate, 2)

		self.add_shipping_rule_to_tax_table(doc, shipping_amount)

	def get_shipping_amount_from_rules(self, value):
		for condition in self.get("conditions"):
			if not condition.to_value or (flt(condition.from_value) <= flt(value) <= flt(condition.to_value)):
				return condition.shipping_amount

		return 0.0

	def validate_countries(self, doc):
		# validate applicable countries
		if self.countries:
			shipping_country = doc.get_shipping_address().get('country')
			if not shipping_country:
				frappe.throw(_('Shipping Address does not have country, which is required for this Shipping Rule'))
			if shipping_country not in [d.country for d in self.countries]:
				frappe.throw(_('Shipping rule not applicable for country {0} in Shipping Address').format(shipping_country))

	def add_shipping_rule_to_tax_table(self, doc, shipping_amount):
		shipping_charge = {
			"charge_type": "Actual",
			"account_head": self.account,
			"cost_center": self.cost_center
		}
		if self.shipping_rule_type == "Selling":
			# check if not applied on purchase
			if not doc.meta.get_field('taxes').options == 'Sales Taxes and Charges':
				frappe.throw(_('Shipping rule only applicable for Selling'))
			shipping_charge["doctype"] = "Sales Taxes and Charges"
		else:
			# check if not applied on sales
			if not doc.meta.get_field('taxes').options == 'Purchase Taxes and Charges':
				frappe.throw(_('Shipping rule only applicable for Buying'))

			shipping_charge["doctype"] = "Purchase Taxes and Charges"
			shipping_charge["category"] = "Valuation and Total"
			shipping_charge["add_deduct_tax"] = "Add"

		existing_shipping_charge = doc.get("taxes", filters=shipping_charge)
		if existing_shipping_charge:
			# take the last record found
			existing_shipping_charge[-1].tax_amount = shipping_amount
		else:
			shipping_charge["tax_amount"] = shipping_amount
			shipping_charge["description"] = self.label
			doc.append("taxes", shipping_charge)

	def sort_shipping_rule_conditions(self):
		"""Sort Shipping Rule Conditions based on increasing From Value"""
		self.shipping_rules_conditions = sorted(self.conditions, key=lambda d: flt(d.from_value))
		for i, d in enumerate(self.conditions):
			d.idx = i + 1

	def validate_overlapping_shipping_rule_conditions(self):
		def overlap_exists_between(num_range1, num_range2):
			"""
				num_range1 and num_range2 are two ranges
				ranges are represented as a tuple e.g. range 100 to 300 is represented as (100, 300)
				if condition num_range1 = 100 to 300
				then condition num_range2 can only be like 50 to 99 or 301 to 400
				hence, non-overlapping condition = (x1 <= x2 < y1 <= y2) or (y1 <= y2 < x1 <= x2)
			"""
			(x1, x2), (y1, y2) = num_range1, num_range2
			separate = (x1 <= x2 <= y1 <= y2) or (y1 <= y2 <= x1 <= x2)
			return (not separate)

		overlaps = []
		for i in range(0, len(self.conditions)):
			for j in range(i+1, len(self.conditions)):
				d1, d2 = self.conditions[i], self.conditions[j]
				if d1.as_dict() != d2.as_dict():
					# in our case, to_value can be zero, hence pass the from_value if so
					range_a = (d1.from_value, d1.to_value or d1.from_value)
					range_b = (d2.from_value, d2.to_value or d2.from_value)
					if overlap_exists_between(range_a, range_b):
						overlaps.append([d1, d2])

		if overlaps:
			company_currency = erpnext.get_company_currency(self.company)
			msgprint(_("Overlapping conditions found between:"))
			messages = []
			for d1, d2 in overlaps:
				messages.append("%s-%s = %s " % (d1.from_value, d1.to_value, fmt_money(d1.shipping_amount, currency=company_currency)) +
					_("and") + " %s-%s = %s" % (d2.from_value, d2.to_value, fmt_money(d2.shipping_amount, currency=company_currency)))

			msgprint("\n".join(messages), raise_exception=OverlappingConditionError)
