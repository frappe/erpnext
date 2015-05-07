# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():					
	for po in frappe.db.sql("""select name from `tabProduction Order` where docstatus < 2""", as_dict=1):
		prod_order = frappe.get_doc("Production Order", po.name)
		if prod_order.operations:
			prod_order.flags.ignore_validate_update_after_submit = True
			prod_order.calculate_time()
			prod_order.save()