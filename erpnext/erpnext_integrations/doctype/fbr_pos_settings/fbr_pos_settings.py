# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


invoice_custom_fields = [
	# At the top
	{"label": "Is FBR POS Invoice", "fieldname": "is_fbr_pos_invoice", "fieldtype": "Check",
		"insert_after": "has_stin", "default": 1, "no_copy": 1},

	# In FBR POS Transaction Details Section
	{"label": "FBR POSID", "fieldname": "fbr_pos_id", "fieldtype": "Int",
		"insert_after": "sec_fbr_pos_transaction_details", "no_copy": 1},
	{"label": "FBR POS InvoiceType", "fieldname": "fbr_pos_invoice_type", "fieldtype": "Data",
		"insert_after": "fbr_pos_id", "read_only": 1, "no_copy": 1},
	{"label": "FBR POS PaymentMode", "fieldname": "fbr_pos_payment_mode", "fieldtype": "Data",
		"insert_after": "fbr_pos_invoice_type", "read_only": 1, "no_copy": 1},

	{"label": "", "fieldname": "cb_fbr_pos_1", "fieldtype": "Column Break",
		"insert_after": "fbr_pos_payment_mode"},

	{"label": "FBR POS TotalSaleValue", "fieldname": "fbr_pos_total_sale_value", "fieldtype": "Currency",
		"options": "Company:company:default_currency",
		"insert_after": "cb_fbr_pos_1", "read_only": 1, "no_copy": 1},
	{"label": "FBR POS Discount", "fieldname": "fbr_pos_discount", "fieldtype": "Currency",
		"options": "Company:company:default_currency",
		"insert_after": "fbr_pos_total_sale_value", "read_only": 1, "no_copy": 1},
	{"label": "FBR POS TotalQuantity", "fieldname": "fbr_pos_total_quantity", "fieldtype": "Float",
		"insert_after": "fbr_pos_discount", "read_only": 1, "no_copy": 1},

	{"label": "", "fieldname": "cb_fbr_pos_2", "fieldtype": "Column Break",
		"insert_after": "fbr_pos_total_quantity"},

	{"label": "FBR POS TotalTaxCharged", "fieldname": "fbr_pos_total_tax_charged", "fieldtype": "Currency",
		"options": "Company:company:default_currency",
		"insert_after": "cb_fbr_pos_2", "read_only": 1, "no_copy": 1},
	{"label": "FBR POS FurtherTax", "fieldname": "fbr_pos_further_tax", "fieldtype": "Currency",
		"options": "Company:company:default_currency",
		"insert_after": "fbr_pos_total_tax_charged", "read_only": 1, "no_copy": 1},
	{"label": "FBR POS TotalBillAmount", "fieldname": "fbr_pos_total_bill_amount", "fieldtype": "Currency",
		"options": "Company:company:default_currency",
		"insert_after": "fbr_pos_further_tax", "read_only": 1, "no_copy": 1},

	{"label": "", "fieldname": "cb_fbr_pos_3", "fieldtype": "Column Break",
		"insert_after": "fbr_pos_total_tax_charged"},

	{"label": "FBR POS InvoiceNumber", "fieldname": "fbr_pos_invoice_no", "fieldtype": "Data",
		"insert_after": "cb_fbr_pos_3", "read_only": 1, "no_copy": 1},
	{"label": "FBR POS QR Code", "fieldname": "fbr_pos_qrcode", "fieldtype": "Barcode",
		"insert_after": "fbr_pos_invoice_no", "read_only": 1, "hidden": 1, "no_copy": 1},
	{"label": "FBR POS JSON Data", "fieldname": "fbr_pos_json_data", "fieldtype": "Code",
		"insert_after": "fbr_pos_qrcode", "read_only": 1, "hidden": 1, "no_copy": 1},

	# FBR POS Item Details Section
	{"label": "FBR POS Item Details", "fieldname": "sec_fbr_pos_item_details", "fieldtype": "Section Break",
		"insert_after": "fbr_pos_json_data", "collapsible": 1,
		"depends_on": "eval:doc.has_stin && doc.is_fbr_pos_invoice"},

	{"label": "FBR POS Items", "fieldname": "fbr_pos_items", "fieldtype": "Table",
		"options": "FBR POS Invoice Item",
		"insert_after": "sec_fbr_pos_item_details", "read_only": 1, "no_copy": 1},
]

for d in invoice_custom_fields:
	d['translatable'] = 0


class FBRPOSSettings(Document):
	def validate(self):
		if self.enable_fbr_pos:
			setup_fbr_pos_fields()
		else:
			check_can_disable_fbr_pos()
			disable_fbr_pos_fields()


def setup_fbr_pos_fields():
	create_custom_fields({
		'Sales Invoice': invoice_custom_fields,
	})


def disable_fbr_pos_fields():
	for custom_field_detail in invoice_custom_fields:
		custom_field_name = frappe.db.get_value('Custom Field',
			dict(dt="Sales Invoice", fieldname=custom_field_detail.get('fieldname')))
		if custom_field_name:
			frappe.delete_doc('Custom Field', custom_field_name)


def check_can_disable_fbr_pos():
	if frappe.db.get_all("Sales Invoice", {'docstatus': 1, 'is_fbr_pos_invoice': 1}, limit=1):
		frappe.throw(_("Cannot disable FBR POS Integration because FBR POS Invoices are already submitted"))
