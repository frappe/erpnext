// Copyright (c) 2016, Dexciss Technology and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Gross Profit Alternate UOM"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_start_date")
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_end_date")
		},
		// {
		// 	"fieldname":"sales_invoice",
		// 	"label": __("Sales Invoice"),
		// 	"fieldtype": "Link",
		// 	"options": "Sales Invoice"
		// },
		{
			"fieldname":"group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": "Invoice\nItem Code\nItem Group\nBrand\nWarehouse\nCustomer\nCustomer Group\nTerritory\nSales Person\nProject",
			"default": "Item Code",
			"read_only": 1,
			"hidden" : 1
		},
	],
	"tree": true,
	"name_field": "parent",
	"parent_field": "parent_invoice",
	"initial_depth": 3,
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (data && (data.indent == 0.0 || row[1].content == "Total")) {
			value = $(`<span>${value}</span>`);
			var $value = $(value).css("font-weight", "bold");
			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
};
