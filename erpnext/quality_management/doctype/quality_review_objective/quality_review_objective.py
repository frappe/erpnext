# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class QualityReviewObjective(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		objective: DF.Text | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		review: DF.TextEditor | None
		status: DF.Literal["Open", "Passed", "Failed"]
		target: DF.Data | None
		uom: DF.Link | None
	# end: auto-generated types

	pass
