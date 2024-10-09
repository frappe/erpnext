# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class PurchaseReceiptItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_zero_valuation_rate: DF.Check
		amount: DF.Currency
		apply_tds: DF.Check
		asset_category: DF.Link | None
		asset_location: DF.Link | None
		barcode: DF.Data | None
		base_amount: DF.Currency
		base_net_amount: DF.Currency
		base_net_rate: DF.Currency
		base_price_list_rate: DF.Currency
		base_rate: DF.Currency
		base_rate_with_margin: DF.Currency
		batch_no: DF.Link | None
		billed_amt: DF.Currency
		bom: DF.Link | None
		brand: DF.Link | None
		conversion_factor: DF.Float
		cost_center: DF.Link | None
		delivery_note_item: DF.Data | None
		description: DF.TextEditor | None
		discount_amount: DF.Currency
		discount_percentage: DF.Percent
		distributed_discount_amount: DF.Currency
		expense_account: DF.Link | None
		from_warehouse: DF.Link | None
		has_item_scanned: DF.Check
		image: DF.Attach | None
		include_exploded_items: DF.Check
		is_fixed_asset: DF.Check
		is_free_item: DF.Check
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data
		item_tax_amount: DF.Currency
		item_tax_rate: DF.Code | None
		item_tax_template: DF.Link | None
		landed_cost_voucher_amount: DF.Currency
		manufacturer: DF.Link | None
		manufacturer_part_no: DF.Data | None
		margin_rate_or_amount: DF.Float
		margin_type: DF.Literal["", "Percentage", "Amount"]
		material_request: DF.Link | None
		material_request_item: DF.Data | None
		net_amount: DF.Currency
		net_rate: DF.Currency
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		price_list_rate: DF.Currency
		pricing_rules: DF.SmallText | None
		product_bundle: DF.Link | None
		project: DF.Link | None
		provisional_expense_account: DF.Link | None
		purchase_invoice: DF.Link | None
		purchase_invoice_item: DF.Data | None
		purchase_order: DF.Link | None
		purchase_order_item: DF.Data | None
		purchase_receipt_item: DF.Data | None
		putaway_rule: DF.Link | None
		qty: DF.Float
		quality_inspection: DF.Link | None
		rate: DF.Currency
		rate_difference_with_purchase_invoice: DF.Currency
		rate_with_margin: DF.Currency
		received_qty: DF.Float
		received_stock_qty: DF.Float
		rejected_qty: DF.Float
		rejected_serial_and_batch_bundle: DF.Link | None
		rejected_serial_no: DF.Text | None
		rejected_warehouse: DF.Link | None
		retain_sample: DF.Check
		return_qty_from_rejected_warehouse: DF.Check
		returned_qty: DF.Float
		rm_supp_cost: DF.Currency
		sales_incoming_rate: DF.Currency
		sales_order: DF.Link | None
		sales_order_item: DF.Data | None
		sample_quantity: DF.Int
		schedule_date: DF.Date | None
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.Text | None
		stock_qty: DF.Float
		stock_uom: DF.Link
		stock_uom_rate: DF.Currency
		subcontracting_receipt_item: DF.Data | None
		supplier_part_no: DF.Data | None
		total_weight: DF.Float
		uom: DF.Link
		use_serial_batch_fields: DF.Check
		valuation_rate: DF.Currency
		warehouse: DF.Link | None
		weight_per_unit: DF.Float
		weight_uom: DF.Link | None
		wip_composite_asset: DF.Link | None
	# end: auto-generated types

	pass
