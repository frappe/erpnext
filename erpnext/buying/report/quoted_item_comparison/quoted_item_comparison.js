// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Quoted Item Comparison"] = {
	"filters": [
	{
		"fieldname":"item",
		"label": __("Item"),
		"fieldtype": "Link",
		"options": "Item",
		"default": ""
		
	}
	]
}
