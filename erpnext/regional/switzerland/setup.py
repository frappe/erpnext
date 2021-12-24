# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup(company=None, patch=True):
    make_custom_fields()

def make_custom_fields():
    custom_fields = {
            'Sales Invoice': [
                dict(fieldname='reference_number', label='Reference Number',
                    fieldtype='Data', insert_after='naming_series', length='25', unique='1', translatable='0'),
                dict(fieldname='reference_number_full', label='Reference Number Full',
                    fieldtype='Data', insert_after='reference_number', length='25', unique='1', translatable='0', hidden='1')
            ]
    }
    create_custom_fields(custom_fields)
