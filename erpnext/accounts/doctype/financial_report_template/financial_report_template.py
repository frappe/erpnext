# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.accounts.doctype.financial_report_template.financial_report_validation import TemplateValidator


class FinancialReportTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.financial_report_row.financial_report_row import FinancialReportRow

		disabled: DF.Check
		is_standard: DF.Check
		module: DF.Link | None
		report_type: DF.Literal["", "Profit and Loss Statement", "Balance Sheet"]
		rows: DF.Table[FinancialReportRow]
		template_name: DF.Data
	# end: auto-generated types

	def validate(self):
		validator = TemplateValidator(self)
		result = validator.validate()

		if not result.is_valid:
			error_messages = [str(issue) for issue in result.issues]
			frappe.throw("<br><br>".join(error_messages))

	def on_update(self):
		self._export_template()

	def _export_template(self):
		from frappe.modules.utils import export_module_json

		return export_module_json(self, self.is_standard == 1, self.module)
