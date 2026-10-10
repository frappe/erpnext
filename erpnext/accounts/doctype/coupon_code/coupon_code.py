# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import strip


class CouponCode(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		coupon_code: DF.Data | None
		coupon_name: DF.Data
		coupon_type: DF.Literal["Promotional", "Gift Card"]
		customer: DF.Link | None
		description: DF.TextEditor | None
		maximum_use: DF.Int
		pricing_rule: DF.Link
		used: DF.Int
		valid_from: DF.Date | None
		valid_upto: DF.Date | None
	# end: auto-generated types

	def autoname(self):
		self.coupon_name = strip(self.coupon_name)
		self.name = self.coupon_name

		if not self.coupon_code:
			if self.coupon_type == "Promotional":
				self.coupon_code = "".join(i for i in self.coupon_name if not i.isdigit())[0:8].upper()
			elif self.coupon_type == "Gift Card":
				self.coupon_code = frappe.generate_hash()[:10].upper()

	def validate(self):
		self.validate_from_to_dates("valid_from", "valid_upto")
		self.validate_pricing_rule()

		if self.coupon_type == "Gift Card":
			self.maximum_use = 1
			if not self.customer:
				frappe.throw(_("Please select the customer."))

	def validate_pricing_rule(self):
		if not self.pricing_rule or self.get("from_external_ecomm_platform"):
			return

		# Allow existing coupons to be updated after their pricing rule is disabled.
		if not (
			self.has_value_changed("pricing_rule") or self.has_value_changed("from_external_ecomm_platform")
		):
			return

		if frappe.db.get_value("Pricing Rule", self.pricing_rule, "disable"):
			frappe.throw(_("Pricing Rule {0} is disabled").format(frappe.bold(self.pricing_rule)))
