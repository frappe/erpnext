// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Transporter Payment Report"] = {
	"filters": [
		{
		"fieldname":"cost_center",
		"label": ("Cost Center"),
		"fieldtype": "Link",
		"options": "Cost Center",
		"width": "100",
		},
		{
		"fieldname": "from_date",
		"label": __("From Date"),
		"fieldtype": "Date",
		"default": frappe.datetime.month_start(),
		},
		{	
		"fieldname": "to_date",
		"label": __("To Date"),
		"fieldtype": "Date",
		"default": frappe.datetime.month_end(),
		},
		{
		"fieldname":"equipment_category",
		"label": ("Equipment Category"),
		"fieldtype": "Link",
		"options": "Equipment Category",
		"width": "100",
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && column.id == "status" ) {
			if( value == 'Paid')
				value = "<span style='color:#286840!important;'>" + value + "</span>";
			else
				value = "<span style='color:#cb5a2a!important;'>" + value + "</span>";
		}
		return value;
	},
};
