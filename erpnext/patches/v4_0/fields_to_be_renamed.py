# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field
from frappe.modules import scrub, get_doctype_module

rename_map = {
	"Quotation Item": [
		["ref_rate", "price_list_rate"],
		["base_ref_rate", "base_price_list_rate"],
		["adj_rate", "discount_percentage"],
		["export_rate", "rate"],
		["basic_rate", "base_rate"],
		["amount", "base_amount"],
		["export_amount", "amount"]
	],

	"Sales Order Item": [
		["ref_rate", "price_list_rate"],
		["base_ref_rate", "base_price_list_rate"],
		["adj_rate", "discount_percentage"],
		["export_rate", "rate"],
		["basic_rate", "base_rate"],
		["amount", "base_amount"],
		["export_amount", "amount"],
		["reserved_warehouse", "warehouse"]
	],

	"Delivery Note Item": [
		["ref_rate", "price_list_rate"],
		["base_ref_rate", "base_price_list_rate"],
		["adj_rate", "discount_percentage"],
		["export_rate", "rate"],
		["basic_rate", "base_rate"],
		["amount", "base_amount"],
		["export_amount", "amount"]
	],

	"Sales Invoice Item": [
		["ref_rate", "price_list_rate"],
		["base_ref_rate", "base_price_list_rate"],
		["adj_rate", "discount_percentage"],
		["export_rate", "rate"],
		["basic_rate", "base_rate"],
		["amount", "base_amount"],
		["export_amount", "amount"]
	],

	"Supplier Quotation Item": [
		["import_ref_rate", "price_list_rate"],
		["purchase_ref_rate", "base_price_list_rate"],
		["discount_rate", "discount_percentage"],
		["import_rate", "rate"],
		["purchase_rate", "base_rate"],
		["amount", "base_amount"],
		["import_amount", "amount"]
	],

	"Purchase Order Item": [
		["import_ref_rate", "price_list_rate"],
		["purchase_ref_rate", "base_price_list_rate"],
		["discount_rate", "discount_percentage"],
		["import_rate", "rate"],
		["purchase_rate", "base_rate"],
		["amount", "base_amount"],
		["import_amount", "amount"]
	],

	"Purchase Receipt Item": [
		["import_ref_rate", "price_list_rate"],
		["purchase_ref_rate", "base_price_list_rate"],
		["discount_rate", "discount_percentage"],
		["import_rate", "rate"],
		["purchase_rate", "base_rate"],
		["amount", "base_amount"],
		["import_amount", "amount"]
	],

	"Purchase Invoice Item": [
		["import_ref_rate", "price_list_rate"],
		["purchase_ref_rate", "base_price_list_rate"],
		["discount_rate", "discount_percentage"],
		["import_rate", "rate"],
		["rate", "base_rate"],
		["amount", "base_amount"],
		["import_amount", "amount"],
		["expense_head", "expense_account"]
	],

	"Item": [
		["purchase_account", "expense_account"],
		["default_sales_cost_center", "selling_cost_center"],
		["cost_center", "buying_cost_center"],
		["default_income_account", "income_account"],
	],
	"Item Price": [
		["ref_rate", "price_list_rate"]
	]
}

def execute():
	for dn in rename_map:
		frappe.reload_doc(get_doctype_module(dn), "doctype", scrub(dn))

	for dt, field_list in rename_map.items():
		for field in field_list:
			rename_field(dt, field[0], field[1])
