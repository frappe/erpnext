// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["POL Receive Report"] = {
	"filters": [
		{
			"fieldname":"branch",
			"label": ("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"width": "100",
		},
		{
			"fieldname":"from_date",
			"label": ("From Date"),
			"fieldtype": "Date",
			"width": "80",
		},
		{
			"fieldname":"to_date",
			"label": ("To Date"),
			"fieldtype": "Date",
			"width": "80",
		},
		{
			"fieldname":"item_name",
			"label": ("Item Name"),
			"fieldtype": "Select",
			"options": ["Petrol","Diesel"],
			"width": "80",
		},
		{
			"fieldname":"Equipment",
			"label": ("equipment"),
			"fieldtype":"Link",
			"options":"Equipment",
			"width": "80",
		}
	]
};
