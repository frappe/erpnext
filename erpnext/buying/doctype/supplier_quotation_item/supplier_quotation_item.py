# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class SupplierQuotationItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		base_amount: DF.Currency
		base_net_amount: DF.Currency
		base_net_rate: DF.Currency
		base_price_list_rate: DF.Currency
		base_rate: DF.Currency
		brand: DF.Link | None
		conversion_factor: DF.Float
		cost_center: DF.Link | None
		description: DF.TextEditor | None
		discount_amount: DF.Currency
		discount_percentage: DF.Percent
		expected_delivery_date: DF.Date | None
		image: DF.Attach | None
		is_free_item: DF.Check
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data | None
		item_tax_rate: DF.Code | None
		item_tax_template: DF.Link | None
		lead_time_days: DF.Int
		manufacturer: DF.Link | None
		manufacturer_part_no: DF.Data | None
		material_request: DF.Link | None
		material_request_item: DF.Data | None
		net_amount: DF.Currency
		net_rate: DF.Currency
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		prevdoc_doctype: DF.Data | None
		price_list_rate: DF.Currency
		pricing_rules: DF.SmallText | None
		project: DF.Link | None
		qty: DF.Float
		rate: DF.Currency
		request_for_quotation: DF.Link | None
		request_for_quotation_item: DF.Data | None
		sales_order: DF.Link | None
		stock_qty: DF.Float
		stock_uom: DF.Link
		supplier_part_no: DF.Data | None
		total_weight: DF.Float
		uom: DF.Link
		warehouse: DF.Link | None
		weight_per_unit: DF.Float
		weight_uom: DF.Link | None
	# end: auto-generated types

	pass
