// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Purchase Order Items To Be Received"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			bold: 1
		},
		{
			fieldname: "qty_field",
			label: __("Quantity Type"),
			fieldtype: "Select",
			options: ["Stock Qty", "Contents Qty", "Transaction Qty"],
			default: "Stock Qty",
			reqd: 1
		},
		{
			fieldname: "name",
			label: __("Purchase Order"),
			fieldtype: "Link",
			options: "Purchase Order"
		},
		{
			fieldname: "transaction_type",
			label: __("Transaction Type"),
			fieldtype: "Link",
			options: "Transaction Type"
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.supplier_query"
				};
			}
		},
		{
			fieldname: "supplier_group",
			label: __("Supplier Group"),
			fieldtype: "Link",
			options: "Supplier Group"
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: function() {
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: {'include_disabled': 1,'include_templates':1}
				}
			},
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group"
		},
		{
			fieldname: "brand",
			label: __("Brand"),
			fieldtype: "Link",
			options: "Brand"
		},
		{
			fieldname: "item_source",
			label: __("Item Source"),
			fieldtype: "Link",
			options: "Item Source"
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: function() {
				return {
					filters: {'company': frappe.query_report.get_filter_value("company")}
				}
			},
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Project', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		}
	],
	formatter: function(value, row, column, data, default_formatter) {
		var style = {};

		if (column.fieldname == "remaining_qty") {
			style['font-weight'] = 'bold';
		}

		if (column.fieldname == "delay_days") {
			if (flt(value) > 0) {
				style['color'] = 'red';
			}
		}

		return default_formatter(value, row, column, data, {css: style});
	},
}
