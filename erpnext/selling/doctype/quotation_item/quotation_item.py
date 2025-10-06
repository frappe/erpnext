# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class QuotationItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_qty: DF.Float
		additional_notes: DF.Text | None
		against_blanket_order: DF.Check
		amount: DF.Currency
		base_amount: DF.Currency
		base_net_amount: DF.Currency
		base_net_rate: DF.Currency
		base_price_list_rate: DF.Currency
		base_rate: DF.Currency
		base_rate_with_margin: DF.Currency
		blanket_order: DF.Link | None
		blanket_order_rate: DF.Currency
		brand: DF.Link | None
		company_total_stock: DF.Float
		conversion_factor: DF.Float
		customer_item_code: DF.Data | None
		description: DF.TextEditor | None
		discount_amount: DF.Currency
		discount_percentage: DF.Percent
		distributed_discount_amount: DF.Currency
		gross_profit: DF.Currency
		has_alternative_item: DF.Check
		image: DF.Attach | None
		is_alternative: DF.Check
		is_free_item: DF.Check
		item_code: DF.Link | None
		item_group: DF.Link | None
		item_name: DF.Data
		item_tax_rate: DF.Code | None
		item_tax_template: DF.Link | None
		margin_rate_or_amount: DF.Float
		margin_type: DF.Literal["", "Percentage", "Amount"]
		net_amount: DF.Currency
		net_rate: DF.Currency
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		prevdoc_docname: DF.DynamicLink | None
		prevdoc_doctype: DF.Link | None
		price_list_rate: DF.Currency
		pricing_rules: DF.SmallText | None
		projected_qty: DF.Float
		qty: DF.Float
		rate: DF.Currency
		rate_with_margin: DF.Currency
		stock_qty: DF.Float
		stock_uom: DF.Link | None
		stock_uom_rate: DF.Currency
		total_weight: DF.Float
		uom: DF.Link
		valuation_rate: DF.Currency
		warehouse: DF.Link | None
		weight_per_unit: DF.Float
		weight_uom: DF.Link | None
	# end: auto-generated types

	pass
