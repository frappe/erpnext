# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	doctypes = frappe.db.sql(""" select name, autoname from `tabDocType`
		where autoname like 'field:%' and allow_rename = 1""", as_dict=1)

	for doctype in doctypes:
		fieldname = doctype.autoname.split(":")[1]
		if fieldname:
			frappe.db.sql(""" update `tab%s` set %s = name """%(doctype.name, fieldname))