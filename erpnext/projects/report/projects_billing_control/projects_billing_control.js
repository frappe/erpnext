// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Projects Billing Control"] = {
	"filters": [
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "Link",
			"options": "Project"
		},
		{
			"fieldname":"when",
			"label": __("When"),
			"fieldtype": "Select",
			"options": "Jan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
			"default": ["1", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
				"Dec"][frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()],
		},
	]
}
