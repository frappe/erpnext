# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("accounts", "doctype", "POS Invoice Merge Log")
	frappe.reload_doc("accounts", "doctype", "POS Closing Entry")
	if frappe.db.count('POS Invoice Merge Log'):
		frappe.db.sql('''
			UPDATE
				`tabPOS Invoice Merge Log` log, `tabPOS Invoice Reference` log_ref
			SET
				log.pos_closing_entry = (
					SELECT clo_ref.parent FROM `tabPOS Invoice Reference` clo_ref
					WHERE clo_ref.pos_invoice = log_ref.pos_invoice
					AND clo_ref.parenttype = 'POS Closing Entry' LIMIT 1
				)
			WHERE
				log_ref.parent = log.name
		''')

		frappe.db.sql('''UPDATE `tabPOS Closing Entry` SET status = 'Submitted' where docstatus = 1''')
		frappe.db.sql('''UPDATE `tabPOS Closing Entry` SET status = 'Cancelled' where docstatus = 2''')
