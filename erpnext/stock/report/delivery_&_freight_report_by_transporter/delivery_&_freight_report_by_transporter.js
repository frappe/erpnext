// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Delivery & Freight Report by Transporter"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": moment().format('YYYY-MM-DD'),
			"reqd": 1,
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": moment().format('YYYY-MM-DD'),
			"reqd": 1,
		},
		{
			"fieldname": "customer_name",
			"fieldtype": "Link",
			"label": "Customer Name",
			"options": "Customer",
		},
		{
			"fieldname": "customer_group",
			"fieldtype": "Link",
			"label": "Customer Group",
			"options": "Customer Group",
			"default": "CSD Distributors",
			"reqd": 1,
		}
	]
};
