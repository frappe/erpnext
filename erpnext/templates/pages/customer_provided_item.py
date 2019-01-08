# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.website.render
from frappe.utils import flt
from frappe import _
from erpnext.controllers.website_list_for_contact import get_customers_suppliers

page_title = "Customer Provided Items"

def get_context(context):
	customer = get_customers_suppliers("Item", frappe.session.user)

	if not customer[0]:
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	items = frappe.db.sql("""select * from `tabItem`
			where is_customer_provided_item=%s and customer = '%s' order by name asc"""%('1', customer[0][0]), as_dict=True)

	for item in items:
		item.stock_qty = flt(frappe.db.sql("""
				select sum(actual_qty) from `tabStock Ledger Entry`
							where item_code = '%s' and docstatus = %s"""%(item.item_code, '1'))[0][0])
		item.reqd_qty = flt(frappe.db.sql("""
			SELECT SUM(GREATEST(woi.required_qty - woi.consumed_qty,0)) AS reqd_qty
			FROM `tabWork Order Item` woi
			LEFT OUTER JOIN `tabWork Order` wo ON wo.name = woi.parent
			WHERE woi.item_code = '%s' and wo.docstatus < 2
				  and wo.status !='%s'"""%(item.item_code, 'Completed'))[0][0])
		item.bal_qty = item.stock_qty - item.reqd_qty

	return {
		"items": items,
		"title": page_title
	}