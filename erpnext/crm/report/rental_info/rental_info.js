// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Rental Info"] = {
	"filters": [
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"reqd": 0,

		},		
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Data",			
			"reqd": 0,

		}
		,		
		{
			"fieldname": "payment_type",
			"label": __("Payment Type"),
			"fieldtype": "Data",			
			"reqd": 0,

		}
		
	]
};
