# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class QualityFeedbackTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.quality_management.doctype.quality_feedback_template_parameter.quality_feedback_template_parameter import (
			QualityFeedbackTemplateParameter,
		)

		parameters: DF.Table[QualityFeedbackTemplateParameter]
		template: DF.Data
	# end: auto-generated types

	pass
