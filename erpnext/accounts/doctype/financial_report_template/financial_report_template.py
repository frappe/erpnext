# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
import shutil

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
		report_type: DF.Literal[
			"", "Profit and Loss Statement", "Balance Sheet", "Cash Flow", "Custom Financial Statement"
		]
		rows: DF.Table[FinancialReportRow]
		template_name: DF.Data
	# end: auto-generated types

	def validate(self):
		validator = TemplateValidator(self)
		result = validator.validate()
		result.notify_user()

	def on_update(self):
		self._export_template()

	def on_trash(self):
		self._delete_template()

	def _export_template(self):
		from frappe.modules.utils import export_module_json

		return export_module_json(self, self.is_standard == 1, self.module)

	def _delete_template(self):
		if not self.is_standard or not frappe.conf.developer_mode:
			return

		module_path = frappe.get_module_path(self.module)
		dir_path = os.path.join(module_path, "financial_report_template", frappe.scrub(self.name))

		shutil.rmtree(dir_path, ignore_errors=True)
