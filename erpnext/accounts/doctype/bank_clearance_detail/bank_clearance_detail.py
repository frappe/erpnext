# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class BankClearanceDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		against_account: DF.Data | None
		amount: DF.Data | None
		cheque_date: DF.Date | None
		cheque_number: DF.Data | None
		clearance_date: DF.Date | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_document: DF.Link | None
		payment_entry: DF.DynamicLink | None
		posting_date: DF.Date | None
	# end: auto-generated types

	pass
