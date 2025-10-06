# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class ShareBalance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Int
		current_state: DF.Literal["", "Issued", "Purchased"]
		from_no: DF.Int
		is_company: DF.Check
		no_of_shares: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rate: DF.Int
		share_type: DF.Link
		to_no: DF.Int
	# end: auto-generated types

	pass
