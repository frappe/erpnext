# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	# Set write permission to permlevel 1 for sales manager role in Quotation doctype
	frappe.db.sql(""" update `tabCustom Docperm` set `tabCustom Docperm`.write = 1
		where `tabCustom Docperm`.parent = 'Quotation' and `tabCustom Docperm`.role = 'Sales Manager'
		and `tabCustom Docperm`.permlevel = 1 """)