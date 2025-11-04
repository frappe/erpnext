# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class QualityInspectionReading(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		acceptance_formula: DF.Code | None
		formula_based_criteria: DF.Check
		manual_inspection: DF.Check
		max_value: DF.Float
		min_value: DF.Float
		numeric: DF.Check
		parameter_group: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reading_10: DF.Data | None
		reading_1: DF.Data | None
		reading_2: DF.Data | None
		reading_3: DF.Data | None
		reading_4: DF.Data | None
		reading_5: DF.Data | None
		reading_6: DF.Data | None
		reading_7: DF.Data | None
		reading_8: DF.Data | None
		reading_9: DF.Data | None
		reading_value: DF.Data | None
		specification: DF.Link
		status: DF.Literal["", "Accepted", "Rejected"]
		value: DF.Data | None
	# end: auto-generated types

	pass
