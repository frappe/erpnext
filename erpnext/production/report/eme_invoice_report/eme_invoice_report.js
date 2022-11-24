// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["EME Invoice Report"] = {
	"filters": [
		{
			"fieldname": "purpose",
			"label": __("Purpose"),
			"fieldtype": "Select",
			"options": ["Expense Account and Expense Head", "Expense Head and Equipment Type"],
			"default": ["Expense Account and Expense Head"],
			"reqd": 1
		},
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			"reqd": 1
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center"
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch"
		},
		{
			"fieldname": "supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier"
		},
		{
			"fieldname": "periodicity",
			"label": __("Periodicity"),
			"fieldtype": "Select",
			"options": [
				{ "value": "Monthly", "label": __("Monthly") },
				{ "value": "Quarterly", "label": __("Quarterly") },
				{ "value": "Half-Yearly", "label": __("Half-Yearly") },
				{ "value": "Yearly", "label": __("Yearly") }
			],
			"default": "Monthly",
			"reqd": 1
		},
		{
			"fieldname": "accumulated_values",
			"label": __("Accumulated Values"),
			"fieldtype": "Check"
		},
		{
			"fieldname": "filter_based_on",
			"label": __("Filter Base On"),
			"fieldtype": "Select",
			"options": ["Fiscal Year","Date Range"],
			"default":"Fiscal Year",
			"hidden":1
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("company"),
			"read_only":1
		},
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if ( column.id == "expense_account" && value.includes(" - SMCL")){
			value = "<span style='text-color: #32CD32 !important; font-weight:bold;'>" + value + "</span>";
		}
		else if ( column.id == "expense_account"){
			value = "<i><span style='text-color: #c0de2a !important;'>" + value + "</span></i>";
		}
		// if( data && column.id == "reading"){
		// 	value = "<span style='color:#3016a6 !important; font-weight:bold'; font-style: italic !important;>" + value + "</span>";
		// }
		return value;
	},
};
