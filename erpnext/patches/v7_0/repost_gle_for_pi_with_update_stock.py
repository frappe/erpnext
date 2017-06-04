# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint

def execute():
	if not cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):
		return

	frappe.reload_doctype("Purchase Invoice")

	for pi in frappe.db.sql("""select name from `tabPurchase Invoice` 
		where update_stock=1 and docstatus=1  order by posting_date asc""", as_dict=1):
		
			frappe.db.sql("""delete from `tabGL Entry` 
				where voucher_type = 'Purchase Invoice' and voucher_no = %s""", pi.name)
				
			pi_doc = frappe.get_doc("Purchase Invoice", pi.name)
			pi_doc.make_gl_entries(repost_future_gle=False)
			frappe.db.commit()