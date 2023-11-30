# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.model.document import Document


class PurchaseOrderItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_qty: DF.Float
		against_blanket_order: DF.Check
		amount: DF.Currency
		apply_tds: DF.Check
		base_amount: DF.Currency
		base_net_amount: DF.Currency
		base_net_rate: DF.Currency
		base_price_list_rate: DF.Currency
		base_rate: DF.Currency
		base_rate_with_margin: DF.Currency
		billed_amt: DF.Currency
		blanket_order: DF.Link | None
		blanket_order_rate: DF.Currency
		bom: DF.Link | None
		brand: DF.Link | None
		company_total_stock: DF.Float
		conversion_factor: DF.Float
		cost_center: DF.Link | None
		delivered_by_supplier: DF.Check
		description: DF.TextEditor | None
		discount_amount: DF.Currency
		discount_percentage: DF.Percent
		expected_delivery_date: DF.Date | None
		expense_account: DF.Link | None
		fg_item: DF.Link | None
		fg_item_qty: DF.Float
		from_warehouse: DF.Link | None
		image: DF.Attach | None
		include_exploded_items: DF.Check
		is_fixed_asset: DF.Check
		is_free_item: DF.Check
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data
		item_tax_rate: DF.Code | None
		item_tax_template: DF.Link | None
		last_purchase_rate: DF.Currency
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
		production_plan: DF.Link | None
		production_plan_item: DF.Data | None
		production_plan_sub_assembly_item: DF.Data | None
		project: DF.Link | None
		qty: DF.Float
		rate: DF.Currency
		rate_with_margin: DF.Currency
		received_qty: DF.Float
		returned_qty: DF.Float
		sales_order: DF.Link | None
		sales_order_item: DF.Data | None
		sales_order_packed_item: DF.Data | None
		schedule_date: DF.Date
		stock_qty: DF.Float
		stock_uom: DF.Link
		stock_uom_rate: DF.Currency
		supplier_part_no: DF.Data | None
		supplier_quotation: DF.Link | None
		supplier_quotation_item: DF.Link | None
		total_weight: DF.Float
		uom: DF.Link
		warehouse: DF.Link | None
		weight_per_unit: DF.Float
		weight_uom: DF.Link | None
		wip_composite_asset: DF.Link | None
	# end: auto-generated types

	pass


def on_doctype_update():
	frappe.db.add_index("Purchase Order Item", ["item_code", "warehouse"])
