# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class PaymentTerm(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		credit_days: DF.Int
		credit_months: DF.Int
		description: DF.SmallText | None
		discount: DF.Float
		discount_type: DF.Literal["Percentage", "Amount"]
		discount_validity: DF.Int
		discount_validity_based_on: DF.Literal[
			"Day(s) after invoice date",
			"Day(s) after the end of the invoice month",
			"Month(s) after the end of the invoice month",
		]
		due_date_based_on: DF.Literal[
			"Day(s) after invoice date",
			"Day(s) after the end of the invoice month",
			"Month(s) after the end of the invoice month",
		]
		invoice_portion: DF.Float
		mode_of_payment: DF.Link | None
		payment_term_name: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.validate_invoice_portion()
		self.validate_days()
		self.validate_discount()

	def validate_invoice_portion(self):
		if not 0 <= flt(self.invoice_portion) <= 100:
			frappe.throw(_("Invoice Portion must be from 0 to 100."), title=_("Invalid Invoice Portion"))

	def validate_days(self):
		for fieldname in ("credit_days", "credit_months", "discount_validity"):
			if cint(self.get(fieldname)) < 0:
				frappe.throw(
					_("{0} cannot be negative.").format(_(self.meta.get_label(fieldname))),
					title=_("Invalid Payment Term"),
				)

	def validate_discount(self):
		if not flt(self.discount):
			return

		if flt(self.discount) < 0 or (self.discount_type == "Percentage" and flt(self.discount) > 100):
			frappe.throw(
				_("Discount must be from 0 to 100 for a percentage, and not negative for an amount."),
				title=_("Invalid Discount"),
			)

		if self.discount_validity_based_on == self.due_date_based_on:
			validity = (
				self.credit_months
				if self.due_date_based_on == "Month(s) after the end of the invoice month"
				else self.credit_days
			)
			if cint(self.discount_validity) > cint(validity):
				frappe.throw(
					_(
						"The discount must end on or before the due date: Discount Validity {0} is more than {1}."
					).format(self.discount_validity, validity),
					title=_("Invalid Discount Validity"),
				)
