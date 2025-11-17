# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document # pragma: no cover


class GLEntryAllocation(Document): # pragma: no cover
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING: # pragma: no cover
		from frappe.types import DF

		allocated_amount: DF.Currency
		credit_gl: DF.Link | None
		debit_gl: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types
	pass
