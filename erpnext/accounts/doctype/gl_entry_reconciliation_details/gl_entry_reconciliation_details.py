# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class GLEntryReconciliationDetails(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING: # pragma: no cover
		from frappe.types import DF

		amount: DF.Currency
		gl_entry: DF.Link | None
		glr_ref_id: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		posting_date: DF.Date | None
	# end: auto-generated types
	pass
