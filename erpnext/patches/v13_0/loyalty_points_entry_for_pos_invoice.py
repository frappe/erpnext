# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
	'''`sales_invoice` field from loyalty point entry is splitted into `invoice_type` & `invoice` fields'''

	loyalty_point_entries = frappe.db.get_all("Loyalty Point Entry", 
		filters={ 'sales_invoice': ('is', 'set') },
		fields=['name', 'sales_invoice'])

	if not loyalty_point_entries:
		return

	frappe.reload_doctype("Loyalty Point Entry")
	for lpe in loyalty_point_entries:
		frappe.db.sql("""UPDATE `tabLoyalty Point Entry` SET invoice_type = 'Sales Invoice', invoice = %s""", (lpe.sales_invoice))