# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.permissions import add_permission, update_permission_property
from erpnext.regional.saudi_arabia.wizard.operations.setup_ksa_vat_setting import (
	create_ksa_vat_setting,
)
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup(company=None, patch=True):
	add_print_formats()
	add_permissions()
	make_custom_fields()


def add_print_formats():
	frappe.reload_doc("regional", "print_format", "detailed_tax_invoice", force=True)
	frappe.reload_doc("regional", "print_format", "simplified_tax_invoice", force=True)
	frappe.reload_doc("regional", "print_format", "tax_invoice", force=True)
	frappe.reload_doc("regional", "print_format", "ksa_vat_invoice", force=True)
	frappe.reload_doc("regional", "print_format", "ksa_pos_invoice", force=True)

	for d in (
		"Simplified Tax Invoice",
		"Detailed Tax Invoice",
		"Tax Invoice",
		"KSA VAT Invoice",
		"KSA POS Invoice",
	):
		frappe.db.set_value("Print Format", d, "disabled", 0)


def add_permissions():
	"""Add Permissions for KSA VAT Setting."""
	add_permission("KSA VAT Setting", "All", 0)
	for role in ("Accounts Manager", "Accounts User", "System Manager"):
		add_permission("KSA VAT Setting", role, 0)
		update_permission_property("KSA VAT Setting", role, 0, "write", 1)
		update_permission_property("KSA VAT Setting", role, 0, "create", 1)

	"""Enable KSA VAT Report"""
	frappe.db.set_value("Report", "KSA VAT", "disabled", 0)


def make_custom_fields():
	"""Create Custom fields
	- QR code Image file
	- Company Name in Arabic
	- Address in Arabic
	"""
	is_zero_rated = dict(
		fieldname="is_zero_rated",
		label="Is Zero Rated",
		fieldtype="Check",
		fetch_from="item_code.is_zero_rated",
		insert_after="description",
		print_hide=1,
	)

	is_exempt = dict(
		fieldname="is_exempt",
		label="Is Exempt",
		fieldtype="Check",
		fetch_from="item_code.is_exempt",
		insert_after="is_zero_rated",
		print_hide=1,
	)

	purchase_invoice_fields = [
		dict(
			fieldname="company_trn",
			label="Company TRN",
			fieldtype="Read Only",
			insert_after="shipping_address",
			fetch_from="company.tax_id",
			print_hide=1,
		),
		dict(
			fieldname="supplier_name_in_arabic",
			label="Supplier Name in Arabic",
			fieldtype="Read Only",
			insert_after="supplier_name",
			fetch_from="supplier.supplier_name_in_arabic",
			print_hide=1,
		),
	]

	sales_invoice_fields = [
		dict(
			fieldname="company_trn",
			label="Company TRN",
			fieldtype="Read Only",
			insert_after="company_address",
			fetch_from="company.tax_id",
			print_hide=1,
		),
		dict(
			fieldname="customer_name_in_arabic",
			label="Customer Name in Arabic",
			fieldtype="Read Only",
			insert_after="customer_name",
			fetch_from="customer.customer_name_in_arabic",
			print_hide=1,
		),
		dict(
			fieldname="ksa_einv_qr",
			label="KSA E-Invoicing QR",
			fieldtype="Attach Image",
			read_only=1,
			no_copy=1,
			hidden=1,
		),
	]

	custom_fields = {
		"Item": [is_zero_rated, is_exempt],
		"Customer": [
			dict(
				fieldname="customer_name_in_arabic",
				label="Customer Name in Arabic",
				fieldtype="Data",
				insert_after="customer_name",
			),
		],
		"Supplier": [
			dict(
				fieldname="supplier_name_in_arabic",
				label="Supplier Name in Arabic",
				fieldtype="Data",
				insert_after="supplier_name",
			),
		],
		"Purchase Invoice": purchase_invoice_fields,
		"Purchase Order": purchase_invoice_fields,
		"Purchase Receipt": purchase_invoice_fields,
		"Sales Invoice": sales_invoice_fields,
		"POS Invoice": sales_invoice_fields,
		"Sales Order": sales_invoice_fields,
		"Delivery Note": sales_invoice_fields,
		"Sales Invoice Item": [is_zero_rated, is_exempt],
		"POS Invoice Item": [is_zero_rated, is_exempt],
		"Purchase Invoice Item": [is_zero_rated, is_exempt],
		"Sales Order Item": [is_zero_rated, is_exempt],
		"Delivery Note Item": [is_zero_rated, is_exempt],
		"Quotation Item": [is_zero_rated, is_exempt],
		"Purchase Order Item": [is_zero_rated, is_exempt],
		"Purchase Receipt Item": [is_zero_rated, is_exempt],
		"Supplier Quotation Item": [is_zero_rated, is_exempt],
		"Address": [
			dict(
				fieldname="address_in_arabic",
				label="Address in Arabic",
				fieldtype="Data",
				insert_after="address_line2",
			)
		],
		"Company": [
			dict(
				fieldname="company_name_in_arabic",
				label="Company Name In Arabic",
				fieldtype="Data",
				insert_after="company_name",
			)
		],
	}

	create_custom_fields(custom_fields, ignore_validate=True, update=True)


def update_regional_tax_settings(country, company):
	create_ksa_vat_setting(company)
