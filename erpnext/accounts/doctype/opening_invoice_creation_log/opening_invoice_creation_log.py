# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class OpeningInvoiceCreationLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		exception: DF.Text | None
		messages: DF.Code | None
		opening_invoice_creation_tool: DF.Link
		reference_name: DF.DynamicLink | None
		reference_type: DF.Link | None
		source_row_index: DF.Int
		success: DF.Check
	# end: auto-generated types

	pass
