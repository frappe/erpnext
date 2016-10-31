# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

def execute():
	if not cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):
		return

	for pi in frappe.db.sql("""select name from `tabPurchase Invoice` 
		where update_stock=1 and docstatus=1  order by posting_date asc""", as_dict=1):
			pi_doc = frappe.get_doc("Purchase Invoice", pi.name)
			pi_doc.make_gl_entries()
			frappe.db.commit()