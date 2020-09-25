# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, os, json
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from erpnext.setup.setup_wizard.operations.taxes_setup import create_sales_tax

def setup(company=None, patch=True):
	make_custom_fields()
	add_print_formats()
	add_custom_roles_for_reports()

	if company:
		create_sales_tax(company)

def make_custom_fields():
	is_zero_rated = dict(fieldname='is_zero_rated', label='Is Zero Rated',
		fieldtype='Check', fetch_from='item_code.is_zero_rated', insert_after='description',
		print_hide=1)
	is_exempt = dict(fieldname='is_exempt', label='Is Exempt',
		fieldtype='Check', fetch_from='item_code.is_exempt', insert_after='is_zero_rated',
		print_hide=1)

	invoice_fields = [
		dict(fieldname='vat_section', label='VAT Details', fieldtype='Section Break',
			insert_after='group_same_items', print_hide=1, collapsible=1),
		dict(fieldname='permit_no', label='Permit Number',
			fieldtype='Data', insert_after='vat_section', print_hide=1),
	]

	purchase_invoice_fields = [
			dict(fieldname='company_trn', label='Company TRN',
				fieldtype='Read Only', insert_after='shipping_address',
				fetch_from='company.tax_id', print_hide=1),
			dict(fieldname='supplier_name_in_arabic', label='Supplier Name in Arabic',
				fieldtype='Read Only', insert_after='supplier_name',
				fetch_from='supplier.supplier_name_in_arabic', print_hide=1),
			dict(fieldname='reverse_charge', label='Reverse Charge Applicable',
				fieldtype='Select', insert_after='permit_no', print_hide=1,
				options='Y\nN', default='N'),
			dict(fieldname='claimable_reverse_charge', label='Claimable Reverse Charge (Percentage)',
				insert_after='reverse_charge', fieldtype='Percent', print_hide=1,
				depends_on="eval:doc.reverse_charge=='Y'", default='100.000'),
		]

	sales_invoice_fields = [
			dict(fieldname='company_trn', label='Company TRN',
				fieldtype='Read Only', insert_after='company_address',
				fetch_from='company.tax_id', print_hide=1),
			dict(fieldname='customer_name_in_arabic', label='Customer Name in Arabic',
				fieldtype='Read Only', insert_after='customer_name',
				fetch_from='customer.customer_name_in_arabic', print_hide=1),
			dict(fieldname='emirate', label='Emirate', insert_after='customer_address',
				fieldtype='Read Only', fetch_from='customer_address.emirates'),
			dict(fieldname='tourist_tax_return', label='Tax Refund provided to Tourists (AED)',
				insert_after='permit_no', fieldtype='Currency', print_hide=1, default='0'),
			dict(fieldname='standard_rated_expenses', label='Standard Rated Expenses (AED)',
				insert_after='tourist_tax_return', fieldtype='Currency', print_hide=1, default='0'),
		]

	invoice_item_fields = [
		dict(fieldname='tax_code', label='Tax Code',
			fieldtype='Read Only', fetch_from='item_code.tax_code', insert_after='description',
			allow_on_submit=1, print_hide=1),
		dict(fieldname='tax_rate', label='Tax Rate',
			fieldtype='Float', insert_after='tax_code',
			print_hide=1, hidden=1, read_only=1),
		dict(fieldname='tax_amount', label='Tax Amount',
			fieldtype='Currency', insert_after='tax_rate',
			print_hide=1, hidden=1, read_only=1, options="currency"),
		dict(fieldname='total_amount', label='Total Amount',
			fieldtype='Currency', insert_after='tax_amount',
			print_hide=1, hidden=1, read_only=1, options="currency"),
	]

	delivery_date_field = [
		dict(fieldname='delivery_date', label='Delivery Date',
			fieldtype='Date', insert_after='item_name', print_hide=1)
	]

	custom_fields = {
		'Item': [
			dict(fieldname='tax_code', label='Tax Code',
				fieldtype='Data', insert_after='item_group'),
			dict(fieldname='is_zero_rated', label='Is Zero Rated',
				fieldtype='Check', insert_after='tax_code',
				print_hide=1),
			dict(fieldname='is_exempt', label='Is Exempt ',
				fieldtype='Check', insert_after='is_zero_rated',
				print_hide=1)
		],
		'Customer': [
			dict(fieldname='customer_name_in_arabic', label='Customer Name in Arabic',
				fieldtype='Data', insert_after='customer_name'),
		],
		'Supplier': [
			dict(fieldname='supplier_name_in_arabic', label='Supplier Name in Arabic',
				fieldtype='Data', insert_after='supplier_name'),
		],
		'Address': [
			dict(fieldname='emirates', label='Emirates', fieldtype='Select', insert_after='state',
			options='Abu Dhabi\nAjman\nDubai\nFujairah\nRas Al Khaimah\nSharjah\nUmm Al Quwain')
		],
		'Purchase Invoice': purchase_invoice_fields + invoice_fields,
		'Purchase Order': purchase_invoice_fields + invoice_fields,
		'Purchase Receipt': purchase_invoice_fields + invoice_fields,
		'Sales Invoice': sales_invoice_fields + invoice_fields,
		'Sales Order': sales_invoice_fields + invoice_fields,
		'Delivery Note': sales_invoice_fields + invoice_fields,
		'Sales Invoice Item': invoice_item_fields + delivery_date_field + [is_zero_rated, is_exempt],
		'Purchase Invoice Item': invoice_item_fields,
		'Sales Order Item': invoice_item_fields,
		'Delivery Note Item': invoice_item_fields,
		'Quotation Item': invoice_item_fields,
		'Purchase Order Item': invoice_item_fields,
		'Purchase Receipt Item': invoice_item_fields,
		'Supplier Quotation Item': invoice_item_fields,
	}

	create_custom_fields(custom_fields)

def add_print_formats():
	frappe.reload_doc("regional", "print_format", "detailed_tax_invoice")
	frappe.reload_doc("regional", "print_format", "simplified_tax_invoice")
	frappe.reload_doc("regional", "print_format", "tax_invoice")

	frappe.db.sql(""" update `tabPrint Format` set disabled = 0 where
		name in('Simplified Tax Invoice', 'Detailed Tax Invoice', 'Tax Invoice') """)

def add_custom_roles_for_reports():
	if not frappe.db.get_value('Custom Role', dict(report='UAE VAT')):
		frappe.get_doc(dict(
			doctype='Custom Role',
			report='UAE VAT',
			roles= [
				dict(role='Accounts User'),
				dict(role='Accounts Manager'),
				dict(role='Auditor')
			]
		)).insert()