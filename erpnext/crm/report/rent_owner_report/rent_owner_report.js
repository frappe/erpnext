// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Rent Owner Report"] = {
	"filters": [
		{
			"fieldname": "dzongkhag",
			"label": __("Dzongkhag"),
			"fieldtype": "Data",			
			"reqd": 0,

		},
		{
			"fieldname": "building_name",
			"label": __("Building Name"),
			"fieldtype": "Data",			
			"reqd": 0,

		}

	]
};
