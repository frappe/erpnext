# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class PromotionalSchemePriceDiscount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		apply_discount_on_rate: DF.Check
		apply_multiple_pricing_rules: DF.Check
		disable: DF.Check
		discount_amount: DF.Currency
		discount_percentage: DF.Float
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
		rate: DF.Currency
		rate_or_discount: DF.Literal["", "Rate", "Discount Percentage", "Discount Amount"]
		rule_description: DF.SmallText
		threshold_percentage: DF.Percent
		validate_applied_rule: DF.Check
		warehouse: DF.Link | None
	# end: auto-generated types

	pass
