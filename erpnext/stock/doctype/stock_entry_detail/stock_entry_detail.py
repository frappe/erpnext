# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class StockEntryDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_qty: DF.Float
		additional_cost: DF.Currency
		against_stock_entry: DF.Link | None
		allow_alternative_item: DF.Check
		allow_zero_valuation_rate: DF.Check
		amount: DF.Currency
		barcode: DF.Data | None
		basic_amount: DF.Currency
		basic_rate: DF.Currency
		batch_no: DF.Link | None
		bom_no: DF.Link | None
		conversion_factor: DF.Float
		cost_center: DF.Link | None
		description: DF.TextEditor | None
		expense_account: DF.Link | None
		has_item_scanned: DF.Check
		image: DF.Attach | None
		is_finished_item: DF.Check
		is_scrap_item: DF.Check
		item_code: DF.Link
		item_group: DF.Data | None
		item_name: DF.Data | None
		job_card_item: DF.Data | None
		material_request: DF.Link | None
		material_request_item: DF.Link | None
		original_item: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		po_detail: DF.Data | None
		project: DF.Link | None
		putaway_rule: DF.Link | None
		qty: DF.Float
		quality_inspection: DF.Link | None
		reference_purchase_receipt: DF.Link | None
		retain_sample: DF.Check
		s_warehouse: DF.Link | None
		sample_quantity: DF.Int
		sco_rm_detail: DF.Data | None
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.Text | None
		set_basic_rate_manually: DF.Check
		ste_detail: DF.Data | None
		stock_uom: DF.Link
		subcontracted_item: DF.Link | None
		t_warehouse: DF.Link | None
		transfer_qty: DF.Float
		transferred_qty: DF.Float
		uom: DF.Link
		use_serial_batch_fields: DF.Check
		valuation_rate: DF.Currency
	# end: auto-generated types

	pass
