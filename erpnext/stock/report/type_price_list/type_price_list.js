// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Type Price List"] = {
	"filters": [
		{
			"fieldname":"type",
			"label": __("Type"),
			"fieldtype": "Select",
			"options": "\nBuying\nSelling",
			"reqd": 1
		},
	]
};
