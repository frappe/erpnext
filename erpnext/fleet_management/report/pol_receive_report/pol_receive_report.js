// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["POL Receive Report"] = {
	"filters": [
		{
			"fieldname":"branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"width": "100",
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default":frappe.datetime.month_start()
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default":frappe.datetime.month_end()
		},
		{
			"fieldname":"item_name",
			"label": __("Item Name"),
			"fieldtype": "Select",
			"options": ["Petrol","Diesel"],
			"width": "80",
		},
		{
			"fieldname":"equipment",
			"label": __("Equipment"),
			"fieldtype":"Link",
			"options":"Equipment",
			"width": "80",
		},
		{
			"fieldname":"aggregate",
			"label": __("Aggregate Data"),
			"fieldtype":"Check",
			"default":1
		}
	]
};
