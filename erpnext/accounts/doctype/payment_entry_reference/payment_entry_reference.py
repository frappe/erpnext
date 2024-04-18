# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class PaymentEntryReference(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		account_type: DF.Data | None
		allocated_amount: DF.Float
		bill_no: DF.Data | None
		due_date: DF.Date | None
		exchange_gain_loss: DF.Currency
		exchange_rate: DF.Float
		outstanding_amount: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_term: DF.Link | None
		payment_type: DF.Data | None
		reference_doctype: DF.Link
		reference_name: DF.DynamicLink
		total_amount: DF.Float
	# end: auto-generated types

	pass
