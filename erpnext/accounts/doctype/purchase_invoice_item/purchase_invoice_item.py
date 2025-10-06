# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class PurchaseInvoiceItem(Document):
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
		base_amount: DF.Currency
		base_net_amount: DF.Currency
		base_net_rate: DF.Currency
		base_price_list_rate: DF.Currency
		base_rate: DF.Currency
		base_rate_with_margin: DF.Currency
		batch_no: DF.Link | None
		bom: DF.Link | None
		brand: DF.Link | None
		conversion_factor: DF.Float
		cost_center: DF.Link | None
		deferred_expense_account: DF.Link | None
		description: DF.TextEditor | None
		discount_amount: DF.Currency
		discount_percentage: DF.Percent
		distributed_discount_amount: DF.Currency
		enable_deferred_expense: DF.Check
		expense_account: DF.Link | None
		from_warehouse: DF.Link | None
		image: DF.Attach | None
		include_exploded_items: DF.Check
		is_fixed_asset: DF.Check
		is_free_item: DF.Check
		item_code: DF.Link | None
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
		po_detail: DF.Data | None
		pr_detail: DF.Data | None
		price_list_rate: DF.Currency
		pricing_rules: DF.SmallText | None
		product_bundle: DF.Link | None
		project: DF.Link | None
		purchase_invoice_item: DF.Data | None
		purchase_order: DF.Link | None
		purchase_receipt: DF.Link | None
		qty: DF.Float
		quality_inspection: DF.Link | None
		rate: DF.Currency
		rate_with_margin: DF.Currency
		received_qty: DF.Float
		rejected_qty: DF.Float
		rejected_serial_and_batch_bundle: DF.Link | None
		rejected_serial_no: DF.Text | None
		rejected_warehouse: DF.Link | None
		rm_supp_cost: DF.Currency
		sales_incoming_rate: DF.Currency
		sales_invoice_item: DF.Data | None
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.Text | None
		service_end_date: DF.Date | None
		service_start_date: DF.Date | None
		service_stop_date: DF.Date | None
		stock_qty: DF.Float
		stock_uom: DF.Link | None
		stock_uom_rate: DF.Currency
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
