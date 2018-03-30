# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doctype("Journal Entry")
	frappe.db.sql("""update `tabJournal Entry` set title =
		if(ifnull(pay_to_recd_from, "")!="", pay_to_recd_from,
			(select account from `tabJournal Entry Account`
				where parent=`tabJournal Entry`.name and idx=1 limit 1))""")
