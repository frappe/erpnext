# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class StockClosingBalance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_qty: DF.Float
		batch_no: DF.Link | None
		company: DF.Link | None
		fifo_queue: DF.LongText | None
		inventory_dimension_key: DF.SmallText | None
		item_code: DF.Link | None
		item_group: DF.Link | None
		item_name: DF.Data | None
		posting_date: DF.Date | None
		posting_datetime: DF.Datetime | None
		posting_time: DF.Time | None
		stock_closing_entry: DF.Link | None
		stock_uom: DF.Link | None
		stock_value: DF.Currency
		stock_value_difference: DF.Currency
		valuation_rate: DF.Currency
		warehouse: DF.Link | None
	# end: auto-generated types

	pass
