# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document # pragma: no cover


class ERPTransaction(Document): # pragma: no cover
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date: DF.Date | None
		deposit: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference_doc: DF.Literal["Payment Entry", "Journal Entry"]
		reference_id: DF.Data | None
		reference_number: DF.Data | None
		remaining_amount: DF.Currency
		withdraw: DF.Currency
	# end: auto-generated types
	pass
