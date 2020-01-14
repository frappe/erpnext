# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	roots = frappe.db.sql("""select lft, rgt, report_type, root_type 
		from `tabAccount` where ifnull(parent_account, '')=''""", as_dict=1)
	for d in roots:
		frappe.db.sql("update `tabAccount` set report_type=%s, root_type=%s where lft > %s and rgt < %s", 
			(d.report_type, d.root_type, d.lft, d.rgt))