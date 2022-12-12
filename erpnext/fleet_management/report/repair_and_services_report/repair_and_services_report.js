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
			"fieldname":"from_date",
			"label": ("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default":frappe.datetime.month_start()
		},
		{
			"fieldname":"to_date",
			"label": ("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default":frappe.datetime.month_end()
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
			"fieldname":"aggregate",
			"label": __("Aggregate Data"),
			"fieldtype":"Check",
			"default":1
		},
		{
			"fieldname": "repair_and_services_type",
			"label": __("Repair and Services Type"),
			"fieldtype": "Select",
			"width": "120",
			"options":["","Preventive Maintenance","Proactive Maintenance","Breakdown Maintenance"]
		},
	]
};
