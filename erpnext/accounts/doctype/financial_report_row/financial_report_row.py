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

		advanced_filtering: DF.Check
		balance_type: DF.Literal[
			"", "Opening Balance", "Closing Balance", "Period Movement (Debits - Credits)"
		]
		bold_text: DF.Check
		calculation_formula: DF.Code | None
		color: DF.Color | None
		data_source: DF.Literal[
			"",
			"Account Data",
			"Calculated Amount",
			"Custom API",
			"Blank Line",
			"Column Break",
			"Section Break",
		]
		display_name: DF.Data | None
		fieldtype: DF.Literal["", "Currency", "Float", "Int", "Percent"]
		hidden_calculation: DF.Check
		hide_when_empty: DF.Check
		include_in_charts: DF.Check
		indentation_level: DF.Int
		italic_text: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference_code: DF.Data | None
		reverse_sign: DF.Check
	# end: auto-generated types

	pass
