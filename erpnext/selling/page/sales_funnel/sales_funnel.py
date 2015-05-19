# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_funnel_data(from_date, to_date):
	active_leads = frappe.db.sql("""select count(*) from `tabLead`
		where (date(`modified`) between %s and %s)
		and status != "Do Not Contact" """, (from_date, to_date))[0][0]

	active_leads += frappe.db.sql("""select count(distinct customer) from `tabContact`
		where (date(`modified`) between %s and %s)
		and status != "Passive" """, (from_date, to_date))[0][0]

	opportunities = frappe.db.sql("""select count(*) from `tabOpportunity`
		where docstatus = 1 and (date(`creation`) between %s and %s)
		and status != "Lost" """, (from_date, to_date))[0][0]

	quotations = frappe.db.sql("""select count(*) from `tabQuotation`
		where docstatus = 1 and (date(`creation`) between %s and %s)
		and status != "Lost" """, (from_date, to_date))[0][0]

	sales_orders = frappe.db.sql("""select count(*) from `tabSales Order`
		where docstatus = 1 and (date(`creation`) between %s and %s)""", (from_date, to_date))[0][0]

	return [
		{ "title": "Active Leads / Customers", "value": active_leads, "color": "#B03B46" },
		{ "title": "Opportunities", "value": opportunities, "color": "#F09C00" },
		{ "title": "Quotations", "value": quotations, "color": "#006685" },
		{ "title": "Sales Orders", "value": sales_orders, "color": "#00AD65" }
	]
