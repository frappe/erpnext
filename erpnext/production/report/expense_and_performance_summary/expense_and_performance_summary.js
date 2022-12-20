// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Expense and Performance Summary"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default":frappe.datetime.year_start(),
			"reqd": 1,
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default":frappe.datetime.get_today(),
			"reqd": 1,
		},
		{
			"fieldname":"branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"reqd": 1,
		},
		{
			"fieldname":"equipment_type",
			"label": __("Equipment Type"),
			"fieldtype": "Link",
			"options": "Equipment Type"
		},
		{
			"fieldname":"equipment",
			"label": __("Equipment"),
			"fieldtype": "Link",
			"options": "Equipment",
        },
		{
			"fieldname":"supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier"
        },
		{
			"fieldname":"company_owned",
			"label": __("Company Owned"),
			"fieldtype": "Check",
			"on_change": function(query_report){
				if (query_report.get_values().company_owned){
					query_report.get_filter_value('supplier',null)
					query_report.refresh();
				}
			}
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if ( value == "Expense Head" || value == "Performance Record") {
			value = "<span style='color:#32CD32!important;font-weight:bold'>" + value + "</span>";
		}
		str = String(value)
		if ( str.includes("Hours")){
			value = "<i><span style='color:#c0de2a!important; font-weight:bold'; font-style: italic !important;'>" + value + "</span></i>";
		}
		return value;
	},
};
