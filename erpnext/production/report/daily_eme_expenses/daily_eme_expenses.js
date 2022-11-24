// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Daily EME Expenses"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default":frappe.datetime.month_start()
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default":frappe.datetime.now_date()
		},
		{
			"fieldname":"equipment",
			"label": __("Equipment"),
			"fieldtype": "Link",
			"options": "Equipment",
			"reqd": 1,
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("company"),
			"read_only":1
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && column.id == "expense_head" ) {
			if( value == 'Total, Actual Hours')
				value = "<i><span style='color:#c0de2a!important; font-weight:bold'; font-style: italic !important;'>" + value + "</span></i>";
			else
				value = "<span style='color:#32CD32!important;font-weight:bold'>" + value + "</span>";
		}
		if ( value.includes("Hours")){
			value = "<i><span style='color:#c0de2a!important; font-weight:bold'; font-style: italic !important;'>" + value + "</span></i>";
		}
		else if( data && column.id == "reading"){
			value = "<span style='color:#3016a6 !important; font-weight:bold'; font-style: italic !important;'>" + value + "</span>";
		}
		return value;
	},
};
