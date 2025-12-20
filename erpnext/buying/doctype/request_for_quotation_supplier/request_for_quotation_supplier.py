# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class RequestforQuotationSupplier(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		contact: DF.Link | None
		email_id: DF.Data | None
		email_sent: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		quote_status: DF.Literal["Pending", "Received"]
		send_email: DF.Check
		supplier: DF.Link
		supplier_name: DF.ReadOnly | None
	# end: auto-generated types

	pass
