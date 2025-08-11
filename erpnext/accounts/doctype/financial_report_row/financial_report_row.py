# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class FinancialReportRow(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		balance_type: DF.Literal["", "Opening", "Closing", "Net Change (Debit - Credit)"]
		formula: DF.Code | None
		hide_if_zero: DF.Check
		indent_level: DF.Int
		inverse_value: DF.Check
		is_bold: DF.Check
		is_italic: DF.Check
		is_statistical: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		row_code: DF.Data | None
		row_label: DF.Data | None
		data_type: DF.Literal["", "Account Balance", "Calculated Total", "Spacing"]
	# end: auto-generated types

	pass
