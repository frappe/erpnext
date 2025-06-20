# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TaxWithholdingEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		exchange_rate: DF.Float
		is_excess_deduction: DF.Check
		is_manual_override: DF.Check
		is_short_deduction: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		short_deduction_reason: DF.Literal["", "Threshold not crossed", "Lower Deduction Certificate"]
		source_date: DF.Date | None
		source_doctype: DF.Link | None
		source_name: DF.DynamicLink | None
		target_date: DF.Date | None
		target_doctype: DF.Link | None
		target_name: DF.DynamicLink | None
		tax_id: DF.Data | None
		tax_rate: DF.Percent
		tax_withheld: DF.Currency
		tax_withholding_category: DF.Link | None
		taxable_amount: DF.Currency
	# end: auto-generated types

	pass
