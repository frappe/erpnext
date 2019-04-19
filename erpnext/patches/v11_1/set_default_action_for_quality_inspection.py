# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
    stock_settings = frappe.get_doc('Stock Settings')
    stock_settings.action_if_quality_inspection_is_not_submitted = "Stop"
    stock_settings.save()