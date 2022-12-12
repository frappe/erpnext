// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["POL Expense Report"] = {
	"filters": [
		{
			"fieldname":"branch",
			"label": ("Fuelbook Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"width": "100",
		},
		{
			"fieldname":"cost_center",
			"label": ("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": "100",
		},
		{
			"fieldname":"from_date",
			"label": ("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default":frappe.datetime.year_start()
		},
		{
			"fieldname":"to_date",
			"label": ("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default":frappe.datetime.year_end()
		},
		{
			"fieldname":"equipment",
			"label": ("Equipment"),
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
