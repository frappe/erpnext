# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class PaymentGatewayAccount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link
		currency: DF.ReadOnly | None
		is_default: DF.Check
		message: DF.SmallText | None
		payment_account: DF.Link
		payment_channel: DF.Literal["", "Email", "Phone"]
		payment_gateway: DF.Link
	# end: auto-generated types

	def autoname(self):
		self.set_currency()
		abbr = frappe.db.get_value("Company", self.company, "abbr")
		self.name = self.payment_gateway + " - " + self.currency + " - " + abbr

	def validate(self):
		self.validate_payment_account()
		self.set_currency()

		self.update_default_payment_gateway()
		self.set_as_default_if_not_set()

	def set_currency(self):
		self.currency = frappe.get_cached_value("Account", self.payment_account, "account_currency")

	def validate_payment_account(self):
		account = frappe.get_cached_value(
			"Account", self.payment_account, ["company", "is_group", "account_type"], as_dict=True
		)
		if (
			not account
			or account.company != self.company
			or account.is_group
			or account.account_type not in ("Bank", "Cash")
		):
			frappe.throw(
				_("Payment Account {0} must be a Bank or Cash account of company {1}, not a group.").format(
					frappe.bold(self.payment_account), frappe.bold(self.company)
				),
				title=_("Invalid Payment Account"),
			)

	def update_default_payment_gateway(self):
		if self.is_default:
			frappe.db.set_value(
				"Payment Gateway Account",
				{
					"is_default": 1,
					"name": ["!=", self.name],
					"company": self.company,
					"currency": self.currency,
				},
				"is_default",
				0,
			)

	def set_as_default_if_not_set(self):
		if not frappe.db.exists(
			"Payment Gateway Account",
			{"is_default": 1, "name": ("!=", self.name), "company": self.company, "currency": self.currency},
		):
			self.is_default = 1
