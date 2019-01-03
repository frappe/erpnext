# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup(company=None, patch=True):
    make_custom_fields()

def make_custom_fields(update=True):
    fiscal_code = dict(fieldname='fiscal_code', label='Fiscal Code', fieldtype='Data', insert_after='tax_id')
    custom_fields = {
        'Company': [
            fiscal_code,
            dict(fieldname='tax_regime', label='Tax Regime', fieldtype='Select', insert_after='fiscal_code', print_hide=1, options='RF01\nRF02\nRF04\nRF05\nRF06\nRF07\nRF08\nRF09\nRF10\nRF11\nRF12\nRF13\nRF14\nRF15\nRF16\nRF17\nRF18\nRF19')
        ],
		'Customer': [
            fiscal_code,
            dict(fieldname='recipient_code', label='Recipient Code', fieldtype='Data', insert_after='fiscal_code', default="0000000"),
            dict(fieldname='recipient_pec', label='Recipient PEC', fieldtype='Data', insert_after='recipient_code', options="Email")
        ],
	}
    print(custom_fields)
    create_custom_fields(custom_fields, ignore_validate = frappe.flags.in_patch, update=update)
