# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_children(parent):
	return frappe.db.sql("""select item_code as value,
		bom_no as parent, qty,
		if(ifnull(bom_no, "")!="", 1, 0) as expandable
		from `tabBOM Item`
		where parent=%s
		order by idx
		""", parent, as_dict=True)
