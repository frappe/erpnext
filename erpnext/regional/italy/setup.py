# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
# coding=utf-8

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from erpnext.regional.italy import fiscal_regimes, tax_exemption_reasons, mode_of_payment_codes, vat_collectability_options

def setup(company=None, patch=True):
    make_custom_fields()
    setup_report()

def make_custom_fields(update=True):
    fiscal_code_field = dict(fieldname='fiscal_code', label='Fiscal Code', fieldtype='Data', insert_after='tax_id', print_hide=1)
    invoice_item_fields = [
        dict(fieldname='tax_rate', label='Tax Rate',
			fieldtype='Float', insert_after='description',
			print_hide=1, hidden=1, read_only=1),
		dict(fieldname='tax_amount', label='Tax Amount',
			fieldtype='Currency', insert_after='tax_rate',
			print_hide=1, hidden=1, read_only=1, options="currency"),
		dict(fieldname='total_amount', label='Total Amount',
			fieldtype='Currency', insert_after='tax_amount',
			print_hide=1, hidden=1, read_only=1, options="currency")
    ]

    custom_fields = {
        'Company': [
            fiscal_code_field,
            dict(fieldname='fiscal_regime', label='Fiscal Regime',
			    fieldtype='Select', insert_after='fiscal_code', print_hide=1,
                options="\n".join(map(lambda x: x.decode('utf-8'), fiscal_regimes)))
        ],
        'Sales Taxes and Charges': [
            dict(fieldname='tax_exemption_reason', label='Tax Exemption Reason',
                fieldtype='Select', insert_after='included_in_print_rate', print_hide=1,
                depends_on='eval:doc.charge_type=="On Net Total" && doc.rate==0.0',
                options="\n" + "\n".join(map(lambda x: x.decode('utf-8'), tax_exemption_reasons))),
            dict(fieldname='tax_exemption_law', label='Tax Exempt Under',
                fieldtype='Text', insert_after='tax_exemption_reason', print_hide=1,
                depends_on='eval:doc.charge_type=="On Net Total" && doc.rate==0.0')
        ],
        'Customer': [
            fiscal_code_field,
            dict(fieldname='recipient_code', label='Recipient Code',
                fieldtype='Data', insert_after='fiscal_code', print_hide=1, default="0000000"),
            dict(fieldname='pec', label='Recipient PEC',
                fieldtype='Data', insert_after='fiscal_code', print_hide=1),
            dict(fieldname='is_public_administration', label='Is Public Administration',
			    fieldtype='Check', insert_after='is_internal_customer', print_hide=1,
                description=_("Set this if the customer is a Public Administration company."),
                depends_on='eval:doc.customer_type=="Company"'),
            dict(fieldname='first_name', label='First Name', fieldtype='Data',
                insert_after='salutation', print_hide=1, depends_on='eval:doc.customer_type!="Company"'),
            dict(fieldname='last_name', label='Last Name', fieldtype='Data',
                insert_after='first_name', print_hide=1, depends_on='eval:doc.customer_type!="Company"')
        ],
        'Mode of Payment': [
            dict(fieldname='mode_of_payment_code', label='Code',
		    fieldtype='Select', insert_after='included_in_print_rate', print_hide=1,
            options="\n".join(map(lambda x: x.decode('utf-8'), mode_of_payment_codes)))
        ],
        'Payment Schedule': [
            dict(fieldname='mode_of_payment_code', label='Code',
                fieldtype='Select', insert_after='mode_of_payment', print_hide=1,
                options="\n".join(map(lambda x: x.decode('utf-8'), mode_of_payment_codes)),
                fetch_from="mode_of_payment.mode_of_payment_code"),
            dict(fieldname='bank_account', label='Bank Account',
                fieldtype='Link', insert_after='mode_of_payment_code', print_hide=1,
                options="Bank Account"),
            dict(fieldname='bank_account_name', label='Bank Account Name',
                fieldtype='Data', insert_after='bank_account', print_hide=1,
                fetch_from="bank_account.account_name", read_only=1),
            dict(fieldname='bank_account_no', label='Bank Account No',
                fieldtype='Data', insert_after='bank_account_name', print_hide=1,
                fetch_from="bank_account.bank_account_no", read_only=1),
            dict(fieldname='bank_account_iban', label='IBAN',
                fieldtype='Data', insert_after='bank_account_name', print_hide=1,
                fetch_from="bank_account.iban", read_only=1),
        ],
        "Sales Invoice": [
            dict(fieldname='vat_collectability', label='VAT Collectability',
			    fieldtype='Select', insert_after='taxes_and_charges', print_hide=1,
                options="\n".join(map(lambda x: x.decode('utf-8'), vat_collectability_options)))
        ],
        'Purchase Invoice Item': invoice_item_fields,
		'Sales Order Item': invoice_item_fields,
		'Delivery Note Item': invoice_item_fields,
        'Sales Invoice Item': invoice_item_fields,
		'Quotation Item': invoice_item_fields,
		'Purchase Order Item': invoice_item_fields,
		'Purchase Receipt Item': invoice_item_fields,
		'Supplier Quotation Item': invoice_item_fields
    }

    create_custom_fields(custom_fields, ignore_validate = frappe.flags.in_patch, update=update)

def setup_report():
    report_name = 'Electronic Invoice Register'

    frappe.db.sql(""" update `tabReport` set disabled = 0 where
        name = %s """, report_name)

    if not frappe.db.get_value('Custom Role', dict(report=report_name)):
        frappe.get_doc(dict(
            doctype='Custom Role',
            report=report_name,
            roles= [
                dict(role='Accounts User'),
                dict(role='Accounts Manager')
            ]
        )).insert()
