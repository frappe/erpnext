# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class PromotionalSchemeProductDiscount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		apply_multiple_pricing_rules: DF.Check
		apply_recursion_over: DF.Float
		disable: DF.Check
		free_item: DF.Link | None
		free_item_rate: DF.Currency
		free_item_uom: DF.Link | None
		free_qty: DF.Float
		is_recursive: DF.Check
		max_amount: DF.Currency
		max_qty: DF.Float
		min_amount: DF.Currency
		min_qty: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		priority: DF.Literal[
			"",
			"1",
			"2",
			"3",
			"4",
			"5",
			"6",
			"7",
			"8",
			"9",
			"10",
			"11",
			"12",
			"13",
			"14",
			"15",
			"16",
			"17",
			"18",
			"19",
			"20",
		]
		recurse_for: DF.Float
		round_free_qty: DF.Check
		rule_description: DF.SmallText
		same_item: DF.Check
		threshold_percentage: DF.Percent
		warehouse: DF.Link | None
	# end: auto-generated types

	pass
