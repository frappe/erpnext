// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Serialized Item Tracking"] = {
	"filters": [
		{
			"fieldname": "link_doctype",
			"label": __("Select..."),
			"fieldtype": "Link",
			"options": "DocType",
			"get_query": () => {
				return {
					filters: { "name": ["in", ["Serial No", "Batch"]] }
				}
			},
			"on_change": () => {
				frappe.query_report.set_filter_value("link_name", null);
			},
			"reqd": 1
		},
		{
			"fieldname": "link_name",
			"label": __("Serial / Batch"),
			"fieldtype": "Dynamic Link",
			"options": "link_doctype",
			"reqd": 1
		},
	]
}