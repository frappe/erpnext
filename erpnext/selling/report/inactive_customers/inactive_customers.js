// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Inactive Customers"] = {
	"filters": [
		{
			"fieldname":"days_since_last_order",
			"label": __("Days Since Last Order"),
			"fieldtype": "Int",
			"default": 60
		},
		{
			"fieldname":"doctype",
			"label": __("Doctype"),
			"fieldtype": "Select",
			"default": "Sales Order",
			"options": "Sales Order\nSales Invoice"
		}
	]
}
