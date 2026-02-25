# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BOMOtherOutput(Document):
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
		qty: DF.Float
		qty_after_process_loss: DF.Float
		stock_qty: DF.Float
		stock_uom: DF.Link | None
		type: DF.Literal["Co-Product", "By-Product", "Scrap", "Finished Good"]
		uom: DF.Link
	# end: auto-generated types

	pass
