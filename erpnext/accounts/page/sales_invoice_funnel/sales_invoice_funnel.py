# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe import _

@frappe.whitelist()
def get_funnel_data(from_date, to_date):

	draft = frappe.db.sql("""select count(*) from `tabSales Invoice` where status='Draft' and (date(`creation`) between %s and %s)""", (from_date, to_date))[0][0]
	paid = frappe.db.sql("""select count(*) from `tabSales Invoice` where status='Paid' and (date(`creation`) between %s and %s)""", (from_date, to_date))[0][0]
	unpaid = frappe.db.sql("""select count(*) from `tabSales Invoice` where status='Unpaid' and (date(`creation`) between %s and %s)""", (from_date, to_date))[0][0]
	return_status = frappe.db.sql("""select count(*) from `tabSales Invoice` where status='Return' and (date(`creation`) between %s and %s)""", (from_date, to_date))[0][0]
	
	return [
		{ "title": _("Draft"), "value": draft, "color": "#B03B66" },
		{ "title": _("Paid"), "value": paid, "color": "#00ADDD" },
		{ "title": _("Unpaid"), "value": unpaid, "color": "#006666" },
		{ "title": _("Return"), "value": return_status, "color": "#F09CCC" },
	]
