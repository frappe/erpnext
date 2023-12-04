# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class PaymentSchedule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		base_payment_amount: DF.Currency
		description: DF.SmallText | None
		discount: DF.Float
		discount_date: DF.Date | None
		discount_type: DF.Literal["Percentage", "Amount"]
		discounted_amount: DF.Currency
		due_date: DF.Date
		invoice_portion: DF.Percent
		mode_of_payment: DF.Link | None
		outstanding: DF.Currency
		paid_amount: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_amount: DF.Currency
		payment_term: DF.Link | None
	# end: auto-generated types

	pass
