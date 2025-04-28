# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class PaymentGatewayAccount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

<<<<<<< HEAD
		company: DF.Link
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
		currency: DF.ReadOnly | None
		is_default: DF.Check
		message: DF.SmallText | None
		payment_account: DF.Link
		payment_channel: DF.Literal["", "Email", "Phone"]
		payment_gateway: DF.Link
	# end: auto-generated types

	def autoname(self):
<<<<<<< HEAD
		abbr = frappe.db.get_value("Company", self.company, "abbr")
		self.name = self.payment_gateway + " - " + self.currency + " - " + abbr
=======
		self.name = self.payment_gateway + " - " + self.currency
>>>>>>> 7c4cf3e834 (Favicon.svg)

	def validate(self):
		self.currency = frappe.get_cached_value("Account", self.payment_account, "account_currency")

		self.update_default_payment_gateway()
		self.set_as_default_if_not_set()

	def update_default_payment_gateway(self):
		if self.is_default:
<<<<<<< HEAD
			frappe.db.set_value(
				"Payment Gateway Account",
				{"is_default": 1, "name": ["!=", self.name], "company": self.company},
				"is_default",
				0,
			)

	def set_as_default_if_not_set(self):
		if not frappe.db.exists(
			"Payment Gateway Account", {"is_default": 1, "name": ("!=", self.name), "company": self.company}
=======
			frappe.db.sql(
				"""update `tabPayment Gateway Account` set is_default = 0
				where is_default = 1 """
			)

	def set_as_default_if_not_set(self):
		if not frappe.db.get_value(
			"Payment Gateway Account", {"is_default": 1, "name": ("!=", self.name)}, "name"
>>>>>>> 7c4cf3e834 (Favicon.svg)
		):
			self.is_default = 1
