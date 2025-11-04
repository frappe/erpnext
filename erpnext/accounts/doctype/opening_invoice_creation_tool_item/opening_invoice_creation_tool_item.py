# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class OpeningInvoiceCreationToolItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cost_center: DF.Link | None
		due_date: DF.Date | None
		invoice_number: DF.Data | None
		item_name: DF.Data | None
		outstanding_amount: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party: DF.DynamicLink
		party_type: DF.Link | None
		posting_date: DF.Date | None
		qty: DF.Data | None
		temporary_opening_account: DF.Link | None
	# end: auto-generated types

	pass
