# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class DeliveryNoteItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_batch_qty: DF.Float
		actual_qty: DF.Float
		against_pick_list: DF.Link | None
		against_sales_invoice: DF.Link | None
		against_sales_order: DF.Link | None
		allow_zero_valuation_rate: DF.Check
		amount: DF.Currency
		barcode: DF.Data | None
		base_amount: DF.Currency
		base_net_amount: DF.Currency
		base_net_rate: DF.Currency
		base_price_list_rate: DF.Currency
		base_rate: DF.Currency
		base_rate_with_margin: DF.Currency
		batch_no: DF.Link | None
		billed_amt: DF.Currency
		brand: DF.Link | None
		company_total_stock: DF.Float
		conversion_factor: DF.Float
		cost_center: DF.Link | None
		customer_item_code: DF.Data | None
		description: DF.TextEditor | None
		discount_amount: DF.Currency
		discount_percentage: DF.Float
		distributed_discount_amount: DF.Currency
		dn_detail: DF.Data | None
		expense_account: DF.Link | None
		grant_commission: DF.Check
		has_item_scanned: DF.Check
		image: DF.Attach | None
		incoming_rate: DF.Currency
		installed_qty: DF.Float
		is_free_item: DF.Check
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data
		item_tax_rate: DF.SmallText | None
		item_tax_template: DF.Link | None
		margin_rate_or_amount: DF.Float
		margin_type: DF.Literal["", "Percentage", "Amount"]
		material_request: DF.Link | None
		material_request_item: DF.Data | None
		net_amount: DF.Currency
		net_rate: DF.Currency
		packed_qty: DF.Float
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		pick_list_item: DF.Data | None
		price_list_rate: DF.Currency
		pricing_rules: DF.SmallText | None
		project: DF.Link | None
		purchase_order: DF.Link | None
		purchase_order_item: DF.Data | None
		qty: DF.Float
		quality_inspection: DF.Link | None
		rate: DF.Currency
		rate_with_margin: DF.Currency
		received_qty: DF.Float
		returned_qty: DF.Float
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.Text | None
		si_detail: DF.Data | None
		so_detail: DF.Data | None
		stock_qty: DF.Float
		stock_uom: DF.Link
		stock_uom_rate: DF.Currency
		target_warehouse: DF.Link | None
		total_weight: DF.Float
		uom: DF.Link
		use_serial_batch_fields: DF.Check
		warehouse: DF.Link | None
		weight_per_unit: DF.Float
		weight_uom: DF.Link | None
	# end: auto-generated types

	pass
