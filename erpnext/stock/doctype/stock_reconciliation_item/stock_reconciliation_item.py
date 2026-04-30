# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class StockReconciliationItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_zero_valuation_rate: DF.Check
		amount: DF.Currency
		amount_difference: DF.Currency
		barcode: DF.Data | None
		batch_no: DF.Link | None
		current_amount: DF.Currency
		current_qty: DF.Float
		current_serial_and_batch_bundle: DF.Link | None
		current_serial_no: DF.LongText | None
		current_valuation_rate: DF.Currency
		has_item_scanned: DF.Data | None
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qty: DF.Float
		quantity_difference: DF.ReadOnly | None
		reconcile_all_serial_batch: DF.Check
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.LongText | None
		stock_uom: DF.Link | None
		use_serial_batch_fields: DF.Check
		valuation_rate: DF.Currency
		warehouse: DF.Link
	# end: auto-generated types

	pass
