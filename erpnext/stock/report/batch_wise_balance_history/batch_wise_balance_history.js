// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Batch-Wise Balance History"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.sys_defaults.year_start_date,
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"get_query": function() {
				return {
					filters: {
						"has_batch_no": 1
					}
				}
			}
		},
		{
			"fieldname":"warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"get_query": function() {
				let company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						"company": company
					}
				}
			}
		},
		{
			"fieldname":"batch_no",
			"label": __("Batch No"),
			"fieldtype": "Link",
			"options": "Batch",
			"get_query": function() {
				let item_code = frappe.query_report.get_filter_value('item_code');
				return {
					filters: {
						"item": item_code
					}
				}
			}
		},
	]
}