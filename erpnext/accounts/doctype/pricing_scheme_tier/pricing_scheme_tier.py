# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PricingSchemeTier(Document):
	"""One slab of a Pricing Scheme.

	Qty bands are in stock UOM, amount bands in company base currency,
	both half-open: min <= basis < max (max 0 = unbounded). The meaning
	of ``value`` follows the parent's effect_type.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		free_item: DF.Link | None
		free_item_rate: DF.Currency
		free_item_uom: DF.Link | None
		free_qty: DF.Float
		margin_type: DF.Literal["", "Percentage", "Amount"]
		max_amount: DF.Currency
		max_qty: DF.Float
		min_amount: DF.Currency
		min_qty: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		recurrence_qty: DF.Float
		round_down_recurrence: DF.Check
		value: DF.Float
	# end: auto-generated types

	pass
