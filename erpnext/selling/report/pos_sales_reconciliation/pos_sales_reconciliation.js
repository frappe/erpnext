// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["POS Sales Reconciliation"] = {
	"filters": [{
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "reqd": 1,
            "width": "80",
            "default": frappe.datetime.month_start()
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "reqd": 1,
            "width": "80",
            "default": frappe.datetime.get_today()
        },
	    {
            "fieldname": "shift",
            "label": __("Shift"),
            "fieldtype": "Link",
            "options": "POS Shift Detail",
            "reqd": 1,
            "width": "80"
        },
        {
            "fieldname": "owner",
            "label": __("Sales Person"),
            "fieldtype": "Link",
            "options": "User",
            "reqd": 1,
            "width": "80"
           
        }

	]
}
