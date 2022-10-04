// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Customer Ledger Summary"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"bold": 1,
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_start_date"),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_end_date"),
			"reqd": 1,
			"width": "60px"
		},
		{
			"fieldname":"party",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			on_change: () => {
				var party = frappe.query_report.get_filter_value('party');
				if (party) {
					frappe.db.get_value('Customer', party, ["tax_id", "customer_name"], function(value) {
						frappe.query_report.set_filter_value('tax_id', value["tax_id"]);
						frappe.query_report.set_filter_value('customer_name', value["customer_name"]);
					});
				} else {
					frappe.query_report.set_filter_value('tax_id', "");
					frappe.query_report.set_filter_value('customer_name', "");
				}
			},
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.customer_query"
				};
			}
		},
		{
			"fieldname":"customer_group",
			"label": __("Customer Group"),
			"fieldtype": "Link",
			"options": "Customer Group"
		},
		{
			"fieldname": "account",
			"label": __("Receivable Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company');
				return {
					"doctype": "Account",
					"filters": {
						"company": company,
						"account_type": "Receivable",
						"is_group": 0
					}
				}
			}
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center"
		},
		{
			"fieldname":"payment_terms_template",
			"label": __("Payment Terms Template"),
			"fieldtype": "Link",
			"options": "Payment Terms Template"
		},
		{
			"fieldname":"territory",
			"label": __("Territory"),
			"fieldtype": "Link",
			"options": "Territory"
		},
		{
			"fieldname":"sales_partner",
			"label": __("Sales Partner"),
			"fieldtype": "Link",
			"options": "Sales Partner"
		},
		{
			"fieldname":"sales_person",
			"label": __("Sales Person"),
			"fieldtype": "Link",
			"options": "Sales Person"
		},
		{
			"fieldname":"tax_id",
			"label": __("Tax Id"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"customer_name",
			"label": __("Customer Name"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			fieldname: "show_deduction_details",
			label: __("Show Deduction Details"),
			fieldtype: "Check",
			default: 1,
		}
	],

	formatter: function (value, row, column, data, default_formatter) {
		var style = {};

		if (["opening_balance", "closing_balance"].includes(column.fieldname)) {
			style['font-weight'] = 'bold';
		}

		if (flt(value) && (column.fieldname == "total_deductions" || column.is_adjustment)) {
			style['color'] = 'red';
		}

		if (flt(value) && column.fieldname == "invoiced_amount") {
			style['color'] = 'blue';
		}

		if (flt(value) && column.fieldname == "paid_amount") {
			style['color'] = 'green';
		}

		if (flt(value) && column.fieldname == "return_amount") {
			style['color'] = 'orange';
		}

		return default_formatter(value, row, column, data, {css: style});
	}
};

erpnext.utils.add_additional_gl_filters('Customer Ledger Summary');
