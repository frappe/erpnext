# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class QualityInspectionReadingEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		max_value: DF.Float
		min_value: DF.Float
		numeric: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reading_value: DF.Data | None
		serial_no: DF.Link | None
		specification: DF.Link
		status: DF.Literal["Accepted", "Rejected"]
		unit_no: DF.Int
	# end: auto-generated types

	pass
