// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Repair And Services Report"] = {
	"filters": [
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Branch"
		},
		{
			"fieldname": "equipment",
			"label": __("Equipment/Vehicle"),
			"fieldtype": "Link",
			"width": "120",
			"options": "Equipment"
		},
		{
			"fieldname": "equipment_type",
			"label": __("Equipment Type"),
			"fieldtype": "Link",
			"width": "120",
			"options": "Equipment Type"
		},
		{
			"fieldname": "equipment_model",
			"label": __("Equipment Model"),
			"fieldtype": "Data",
			"width": "120",
		},
	]
};
