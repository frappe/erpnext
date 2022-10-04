// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Supplier Ledger Summary"] = {
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
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			on_change: () => {
				var party = frappe.query_report.get_filter_value('party');
				if (party) {
					frappe.db.get_value('Supplier', party, ["tax_id", "supplier_name"], function(value) {
						frappe.query_report.set_filter_value('tax_id', value["tax_id"]);
						frappe.query_report.set_filter_value('supplier_name', value["supplier_name"]);
					});
				} else {
					frappe.query_report.set_filter_value('tax_id', "");
					frappe.query_report.set_filter_value('supplier_name', "");
				}
			}
		},
		{
			"fieldname":"supplier_group",
			"label": __("Supplier Group"),
			"fieldtype": "Link",
			"options": "Supplier Group"
		},
		{
			"fieldname": "account",
			"label": __("Payable Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company');
				return {
					"doctype": "Account",
					"filters": {
						"company": company,
						"account_type": "Payable",
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
			"fieldname":"tax_id",
			"label": __("Tax Id"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"supplier_name",
			"label": __("Supplier Name"),
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
			style['color'] = 'purple';
		}

		if (flt(value) && column.fieldname == "invoiced_amount") {
			style['color'] = 'red';
		}

		if (flt(value) && column.fieldname == "paid_amount") {
			style['color'] = 'green';
		}

		if (flt(value) && column.fieldname == "return_amount") {
			style['color'] = 'blue';
		}

		return default_formatter(value, row, column, data, {css: style});
	}
};

erpnext.utils.add_additional_gl_filters('Supplier Ledger Summary');
