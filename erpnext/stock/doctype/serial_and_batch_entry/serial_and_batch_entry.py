# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SerialandBatchEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		batch_no: DF.Link | None
		delivered_qty: DF.Float
		incoming_rate: DF.Float
		is_outward: DF.Check
		outgoing_rate: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qty: DF.Float
		reference_for_reservation: DF.Data | None
		serial_no: DF.Link | None
		stock_queue: DF.SmallText | None
		stock_value_difference: DF.Float
		warehouse: DF.Link | None
	# end: auto-generated types

	pass
