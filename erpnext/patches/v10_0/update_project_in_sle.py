# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for doctype in ['Sales Invoice', 'Delivery Note', 'Stock Entry']:
		frappe.db.sql(""" update
				`tabStock Ledger Entry` sle, `tab{0}` parent_doc
			set
				sle.project = parent_doc.project
			where
				sle.voucher_no = parent_doc.name and sle.voucher_type = %s and sle.project is null
				and parent_doc.project is not null and parent_doc.project != ''""".format(doctype), doctype)
