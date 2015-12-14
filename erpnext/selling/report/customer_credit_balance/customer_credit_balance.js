// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Credit Balance"] = {
	"filters": [
		{
			"fieldname":"organization",
			"label": __("organization"),
			"fieldtype": "Link",
			"options": "organization",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("organization")
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		}
	]
}
