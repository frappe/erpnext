# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class OverduePayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		discounted_amount: DF.Currency
		due_date: DF.Date | None
		dunning_level: DF.Int
		interest: DF.Currency
		invoice_portion: DF.Percent
		mode_of_payment: DF.Link | None
		outstanding: DF.Currency
		overdue_days: DF.Data | None
		paid_amount: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_amount: DF.Currency
		payment_schedule: DF.Data | None
		payment_term: DF.Link | None
		sales_invoice: DF.Link
	# end: auto-generated types

	pass
