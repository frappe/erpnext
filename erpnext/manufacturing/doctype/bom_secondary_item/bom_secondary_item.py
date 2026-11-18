# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import flt


class BOMSecondaryItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		base_cost: DF.Currency
		conversion_factor: DF.Float
		cost: DF.Currency
		cost_allocation_per: DF.Percent
		description: DF.TextEditor | None
		image: DF.AttachImage | None
		item_code: DF.Link
		item_name: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		process_loss_per: DF.Percent
		process_loss_qty: DF.Float
		qty: DF.Float
		secondary_item_type: DF.Literal["", "Co-Product", "By-Product", "Scrap", "Additional Finished Good"]
		stock_qty: DF.Float
		stock_uom: DF.Link | None
		uom: DF.Link
		valuation_type: DF.Literal["Valuation Rate", "% of Component Cost", "Manual"]
	# end: auto-generated types

	pass


def get_manual_rate(row) -> float:
	"""Rate of a Manual row: its cost is for the qty made, net of process loss."""
	made_qty = flt(row.stock_qty) * (1 - flt(row.process_loss_per) / 100)
	return flt(row.base_cost) / made_qty if made_qty else 0
