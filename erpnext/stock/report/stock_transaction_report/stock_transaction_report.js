// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Stock Transaction Report"] = {
	"filters": [
		{
			"fieldname":"purpose",
			"label": __("Purpose"),
			"fieldtype": "Select",
			"width": "80",
			"options": ["","Material Issue", "Material Transfer"],
			"reqd": 1,
			on_change:function(query){
				purpose=frappe.query_report.get_filter_value('purpose')
				if (str(purpose) == 'Material Issue'){
					frappe.query_report.get_filter('warehouse').toggle(false)
				} 
				else {
					frappe.query_report.get_filter('warehouse').toggle(true)
				}
			}
		},

		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": sys_defaults.year_start_date,
		},

		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today()
		},

		{
			"fieldname": "s_warehouse",
			"label": __("Source Warehouse"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Warehouse"
		},
		{
			"fieldname": "warehouse",
			"label": __("Target Warehouse"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Warehouse"
		},
		{
			"fieldname": "item_code",
			"label": __("Material Code"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Item"
		},
	]
};
