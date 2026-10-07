# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class QualityInspectionTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.item_quality_inspection_parameter.item_quality_inspection_parameter import (
			ItemQualityInspectionParameter,
		)

		item_quality_inspection_parameter: DF.Table[ItemQualityInspectionParameter]
		quality_inspection_template_name: DF.Data
	# end: auto-generated types

	def validate(self):
		for row in self.item_quality_inspection_parameter:
			self.validate_acceptance_formula(row)

	def validate_acceptance_formula(self, row):
		if row.formula_based_criteria and not row.acceptance_formula:
			frappe.throw(
				_("Row #{0}: Acceptance Criteria Formula is required for parameter {1}").format(
					row.idx, frappe.bold(row.specification)
				)
			)


def get_template_details(template):
	if not template:
		return []

	return frappe.get_all(
		"Item Quality Inspection Parameter",
		fields=[
			"specification",
			"value",
			"acceptance_formula",
			"numeric",
			"formula_based_criteria",
			"min_value",
			"max_value",
		],
		filters={"parenttype": "Quality Inspection Template", "parent": template},
		order_by="idx",
	)
