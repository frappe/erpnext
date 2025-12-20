# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BulkTransactionLogDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date: DF.Date | None
		error_description: DF.LongText | None
		from_doctype: DF.Link | None
		retried: DF.Int
		time: DF.Time | None
		to_doctype: DF.Link | None
		transaction_name: DF.DynamicLink | None
		transaction_status: DF.Data | None
	# end: auto-generated types

	pass
