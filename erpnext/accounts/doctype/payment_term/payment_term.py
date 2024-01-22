# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


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

	pass
