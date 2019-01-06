# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
# coding=utf-8

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from erpnext.regional.italy import fiscal_regimes, tax_exemption_reasons

def setup(company=None, patch=True):
	make_custom_fields()

def make_custom_fields(update=True):
    fiscal_code_field = dict(fieldname='fiscal_code', label='Fiscal Code', fieldtype='Data', insert_after='tax_id', print_hide=1)
    custom_fields = {
        'Company': [
            fiscal_code_field,
            dict(fieldname='fiscal_regime', label='Fiscal Regime',
			    fieldtype='Select', insert_after='fiscal_code', print_hide=1,                
                options="\n".join(map(lambda x: x.decode('utf-8'), fiscal_regimes)))
        ],
        'Customer': [
            fiscal_code_field,
            dict(fieldname='recipient_code', label='Recipient Code',
                fieldtype='Data', insert_after='fiscal_code', print_hide=1, default="0000000"),
            dict(fieldname='pec', label='Recipient PEC',
                fieldtype='Data', insert_after='fiscal_code', print_hide=1)
        ],
        'Sales Taxes and Charges': [
            dict(fieldname='tax_exemption_reason', label='Tax Exemption Reason',
		    fieldtype='Select', insert_after='included_in_print_rate', print_hide=1,
            options="\n".join(map(lambda x: x.decode('utf-8'), tax_exemption_reasons)))
        ]
    }

    create_custom_fields(custom_fields, ignore_validate = frappe.flags.in_patch, update=update)
