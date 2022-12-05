// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Production Summary"] = {
	onload:function(query_report){
		if  (query_report.get_filter_values("periodicity").periodicity != 'Daily'){
			frappe.query_report.toggle_filter_display('fiscal_year', false);
			frappe.query_report.toggle_filter_display('from_date', true);
			frappe.query_report.toggle_filter_display('to_date', true);
		}else{
			frappe.query_report.toggle_filter_display('fiscal_year', true);
			frappe.query_report.toggle_filter_display('from_date', false);
			frappe.query_report.toggle_filter_display('to_date', false);
		}
		if  (query_report.get_filter_values("periodicity").periodicity == 'Yearly'){
			frappe.query_report.toggle_filter_display('to_fiscal_year', false);
		}else{
			frappe.query_report.toggle_filter_display('to_fiscal_year', true);
		}
		query_report.refresh()

	},
	"filters": [
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
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname": "to_warehouse",
			"label": __("Transfer to Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname": "location",
			"label": __("Location"),
			"fieldtype": "Link",
			"options": "Location"
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
			"fieldname": "periodicity",
			"label": __("Periodicity"),
			"fieldtype": "Select",
			"options": [
				{ "value": "Daily", "label": __("Daily") },
				{ "value": "Monthly", "label": __("Monthly") },
				{ "value": "Quarterly", "label": __("Quarterly") },
				{ "value": "Half-Yearly", "label": __("Half-Yearly") },
				{ "value": "Yearly", "label": __("Yearly") }
			],
			"default": "Daily",
			"reqd": 1,
			"on_change":(query_report)=>{
				if  (query_report.get_filter_values("periodicity").periodicity != 'Daily'){
					frappe.query_report.toggle_filter_display('fiscal_year', false);
					frappe.query_report.toggle_filter_display('from_date', true);
					frappe.query_report.toggle_filter_display('to_date', true);
				}else{
					frappe.query_report.toggle_filter_display('fiscal_year', true);
					frappe.query_report.toggle_filter_display('from_date', false);
					frappe.query_report.toggle_filter_display('to_date', false);
				}
				if  (query_report.get_filter_values("periodicity").periodicity == 'Yearly'){
					frappe.query_report.toggle_filter_display('to_fiscal_year', false);
				}else{
					frappe.query_report.toggle_filter_display('to_fiscal_year', true);
				}
				query_report.refresh()
			}
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
			"fieldname": "to_fiscal_year",
			"label": __("To Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start()
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default":frappe.datetime.get_today()
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("company"),
			"read_only":1
		}
	]
}
