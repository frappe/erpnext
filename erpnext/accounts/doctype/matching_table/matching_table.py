# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document # pragma: no cover


class MatchingTable(Document): # pragma: no cover
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bank_transaction_id: DF.Link | None
		matched_amount: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference_id: DF.DynamicLink | None
		reference_to: DF.Literal["Payment Entry", "Journal Entry"]
	# end: auto-generated types
	pass
