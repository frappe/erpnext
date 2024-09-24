# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


# import frappe
from erpnext.accounts.doctype.sales_invoice_item.sales_invoice_item import SalesInvoiceItem


class POSInvoiceItem(SalesInvoiceItem):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_batch_qty: DF.Float
		actual_qty: DF.Float
		allow_zero_valuation_rate: DF.Check
		amount: DF.Currency
		asset: DF.Link | None
		barcode: DF.Data | None
		base_amount: DF.Currency
		base_net_amount: DF.Currency
		base_net_rate: DF.Currency
		base_price_list_rate: DF.Currency
		base_rate: DF.Currency
		base_rate_with_margin: DF.Currency
		batch_no: DF.Link | None
		brand: DF.Data | None
		conversion_factor: DF.Float
		cost_center: DF.Link
		customer_item_code: DF.Data | None
		deferred_revenue_account: DF.Link | None
		delivered_by_supplier: DF.Check
		delivered_qty: DF.Float
		delivery_note: DF.Link | None
		description: DF.TextEditor
		discount_amount: DF.Currency
		discount_percentage: DF.Percent
		distributed_discount_amount: DF.Currency
		dn_detail: DF.Data | None
		enable_deferred_revenue: DF.Check
		expense_account: DF.Link | None
		finance_book: DF.Link | None
		grant_commission: DF.Check
		has_item_scanned: DF.Check
		image: DF.Attach | None
		income_account: DF.Link
		is_fixed_asset: DF.Check
		is_free_item: DF.Check
		item_code: DF.Link | None
		item_group: DF.Link | None
		item_name: DF.Data
		item_tax_rate: DF.SmallText | None
		item_tax_template: DF.Link | None
		margin_rate_or_amount: DF.Float
		margin_type: DF.Literal["", "Percentage", "Amount"]
		net_amount: DF.Currency
		net_rate: DF.Currency
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		pos_invoice_item: DF.Data | None
		price_list_rate: DF.Currency
		pricing_rules: DF.SmallText | None
		project: DF.Link | None
		qty: DF.Float
		quality_inspection: DF.Link | None
		rate: DF.Currency
		rate_with_margin: DF.Currency
		sales_order: DF.Link | None
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.Text | None
		service_end_date: DF.Date | None
		service_start_date: DF.Date | None
		service_stop_date: DF.Date | None
		so_detail: DF.Data | None
		stock_qty: DF.Float
		stock_uom: DF.Link | None
		target_warehouse: DF.Link | None
		total_weight: DF.Float
		uom: DF.Link
		use_serial_batch_fields: DF.Check
		warehouse: DF.Link | None
		weight_per_unit: DF.Float
		weight_uom: DF.Link | None
	# end: auto-generated types

	pass
