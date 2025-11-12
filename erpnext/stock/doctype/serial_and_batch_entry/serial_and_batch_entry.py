# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
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
		posting_datetime: DF.Datetime | None
		qty: DF.Float
		reference_for_reservation: DF.Data | None
		serial_no: DF.Link | None
		stock_queue: DF.SmallText | None
		stock_value_difference: DF.Float
		type_of_transaction: DF.Data | None
		voucher_detail_no: DF.Data | None
		voucher_no: DF.Data | None
		voucher_type: DF.Data | None
		warehouse: DF.Link | None
	# end: auto-generated types

	pass


def on_doctype_update():
	frappe.db.add_index("Serial and Batch Entry", ["warehouse", "batch_no", "posting_datetime"])
