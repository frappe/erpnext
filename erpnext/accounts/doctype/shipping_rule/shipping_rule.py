# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _, msgprint, throw
from frappe.utils import flt, fmt_money
from frappe.model.document import Document

class OverlappingConditionError(frappe.ValidationError): pass
class FromGreaterThanToError(frappe.ValidationError): pass
class ManyBlankToValuesError(frappe.ValidationError): pass

class ShippingRule(Document):
	def validate(self):
		self.validate_value("calculate_based_on", "in", ["Net Total", "Net Weight"])
		self.conditions = self.get("conditions")
		self.validate_from_to_values()
		self.sort_shipping_rule_conditions()
		self.validate_overlapping_shipping_rule_conditions()

		if self.worldwide_shipping:
			self.countries = []

		elif not len([d.country for d in self.countries if d.country]):
			frappe.throw(_("Please specify a country for this Shipping Rule or check Worldwide Shipping"))

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

	def sort_shipping_rule_conditions(self):
		"""Sort Shipping Rule Conditions based on increasing From Value"""
		self.shipping_rules_conditions = sorted(self.conditions, key=lambda d: flt(d.from_value))
		for i, d in enumerate(self.conditions):
			d.idx = i + 1

	def validate_overlapping_shipping_rule_conditions(self):
		def overlap_exists_between((x1, x2), (y1, y2)):
			"""
				(x1, x2) and (y1, y2) are two ranges
				if condition x = 100 to 300
				then condition y can only be like 50 to 99 or 301 to 400
				hence, non-overlapping condition = (x1 <= x2 < y1 <= y2) or (y1 <= y2 < x1 <= x2)
			"""
			separate = (x1 <= x2 <= y1 <= y2) or (y1 <= y2 <= x1 <= x2)
			return (not separate)

		overlaps = []
		for i in xrange(0, len(self.conditions)):
			for j in xrange(i+1, len(self.conditions)):
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
