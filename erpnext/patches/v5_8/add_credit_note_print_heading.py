# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute():
	for print_heading in (_("Credit Note"), _("Debit Note")):
		if not frappe.db.exists("Print Heading", print_heading):
			frappe.get_doc({
				"doctype": "Print Heading",
				"print_heading": print_heading
			}).insert()
