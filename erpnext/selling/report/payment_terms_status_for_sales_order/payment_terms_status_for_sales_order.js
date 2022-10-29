// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

function get_filters() {
	let filters = [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"period_start_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname":"period_end_date",
			"label": __("End Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"customer_group",
			"label": __("Customer Group"),
			"fieldtype": "Link",
			"width": 100,
			"options": "Customer Group",
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"width": 100,
			"options": "Customer",
			"get_query": () => {
				var customer_group = frappe.query_report.get_filter_value('customer_group');
				return{
					"query": "erpnext.selling.report.payment_terms_status_for_sales_order.payment_terms_status_for_sales_order.get_customers_or_items",
					"filters": [
						['Customer', 'disabled', '=', '0'],
						['Customer Group','name', '=', customer_group]
					]
				}
			}
		},
		{
			"fieldname":"item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"width": 100,
			"options": "Item Group",

		},
		{
			"fieldname":"item",
			"label": __("Item"),
			"fieldtype": "Link",
			"width": 100,
			"options": "Item",
			"get_query": () => {
				var item_group = frappe.query_report.get_filter_value('item_group');
				return{
					"query": "erpnext.selling.report.payment_terms_status_for_sales_order.payment_terms_status_for_sales_order.get_customers_or_items",
					"filters": [
						['Item', 'disabled', '=', '0'],
						['Item Group','name', '=', item_group]
					]
				}
			}
		},
		{
			"fieldname":"from_due_date",
			"label": __("From Due Date"),
			"fieldtype": "Date",
		},
		{
			"fieldname":"to_due_date",
			"label": __("To Due Date"),
			"fieldtype": "Date",
		},
		{
			"fieldname":"status",
			"label": __("Status"),
			"fieldtype": "MultiSelectList",
			"width": 100,
			get_data: function(txt) {
				let status = ["Overdue", "Unpaid", "Completed", "Partly Paid"]
				let options = []
				for (let option of status){
					options.push({
						"value": option,
						"label": __(option),
						"description": ""
					})
				}
				return options
			}
		},
	]
	return filters;
}

frappe.query_reports["Payment Terms Status for Sales Order"] = {
	"filters": get_filters(),
	"formatter": function(value, row, column, data, default_formatter){
		if(column.fieldname == 'invoices' && value) {
			invoices = value.split(',');
			const invoice_formatter = (prev_value, curr_value) => {
				if(prev_value != "") {
					return prev_value + ", " + default_formatter(curr_value, row, column, data);
				}
				else {
					return default_formatter(curr_value, row, column, data);
				}
			}
			return invoices.reduce(invoice_formatter, "")
		}
		else if (column.fieldname == 'paid_amount' && value){
			formatted_value = default_formatter(value, row, column, data);
			if(value > 0) {
				formatted_value = "<span style='color:green;'>" + formatted_value + "</span>"
			}
			return formatted_value;
		}
		else if (column.fieldname == 'status' && value == 'Completed'){
			return "<span style='color:green;'>" + default_formatter(value, row, column, data) + "</span>";
		}

		return default_formatter(value, row, column, data);
	},

};
