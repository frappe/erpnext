# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import re

def execute():
	for name, html in frappe.db.sql("""select name, html from `tabPrint Format`
		where standard = 'No' and html like '%%purchase\\_tax\\_details%%'"""):
			html = re.sub(r"\bpurchase_tax_details\b", "other_charges", html)
			frappe.db.set_value("Print Format", name, "html", html)
