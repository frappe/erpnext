# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class Cheque(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amount: DF.Currency
		bank_account: DF.Link
		cancellation_reason: DF.Autocomplete | None
		cheque_book: DF.Link
		cheque_date: DF.Date | None
		cheque_no: DF.Data
		company: DF.Link
		currency: DF.Link | None
		party_name: DF.Data | None
		payment_entry: DF.Link | None
		remarks: DF.SmallText | None
		status: DF.Literal["Available", "Issued", "Cancelled"]
	# end: auto-generated types

	pass
