# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Quotation")
	frappe.db.sql(""" UPDATE `tabQuotation` set customer_lead = lead WHERE quotation_to = 'Lead' """)
	frappe.db.sql(""" UPDATE `tabQuotation` set customer_lead = customer WHERE quotation_to = 'Customer' """)