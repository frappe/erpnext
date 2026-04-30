# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class AssetFinanceBook(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		daily_prorata_based: DF.Check
		depreciation_method: DF.Literal[
			"", "Straight Line", "Double Declining Balance", "Written Down Value", "Manual"
		]
		depreciation_start_date: DF.Date | None
		expected_value_after_useful_life: DF.Currency
		finance_book: DF.Link | None
		frequency_of_depreciation: DF.Int
		increase_in_asset_life: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rate_of_depreciation: DF.Percent
		salvage_value_percentage: DF.Percent
		shift_based: DF.Check
		total_number_of_booked_depreciations: DF.Int
		total_number_of_depreciations: DF.Int
		value_after_depreciation: DF.Currency
	# end: auto-generated types

	pass
