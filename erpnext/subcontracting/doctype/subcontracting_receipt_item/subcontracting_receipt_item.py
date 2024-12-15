# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SubcontractingReceiptItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		additional_cost_per_qty: DF.Currency
		amount: DF.Currency
		batch_no: DF.Link | None
		bom: DF.Link | None
		brand: DF.Link | None
		conversion_factor: DF.Float
		cost_center: DF.Link | None
		description: DF.TextEditor | None
		expense_account: DF.Link | None
		image: DF.Attach | None
		include_exploded_items: DF.Check
		is_scrap_item: DF.Check
		item_code: DF.Link
		item_name: DF.Data | None
		job_card: DF.Link | None
		manufacturer: DF.Link | None
		manufacturer_part_no: DF.Data | None
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		project: DF.Link | None
		purchase_order: DF.Link | None
		purchase_order_item: DF.Data | None
		qty: DF.Float
		quality_inspection: DF.Link | None
		rate: DF.Currency
		received_qty: DF.Float
		reference_name: DF.Data | None
		rejected_qty: DF.Float
		rejected_serial_and_batch_bundle: DF.Link | None
		rejected_serial_no: DF.SmallText | None
		rejected_warehouse: DF.Link | None
		returned_qty: DF.Float
		rm_cost_per_qty: DF.Currency
		rm_supp_cost: DF.Currency
		schedule_date: DF.Date | None
		scrap_cost_per_qty: DF.Float
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.SmallText | None
		service_cost_per_qty: DF.Currency
		stock_uom: DF.Link
		subcontracting_order: DF.Link | None
		subcontracting_order_item: DF.Data | None
		subcontracting_receipt_item: DF.Data | None
		use_serial_batch_fields: DF.Check
		warehouse: DF.Link | None
	# end: auto-generated types

	pass
