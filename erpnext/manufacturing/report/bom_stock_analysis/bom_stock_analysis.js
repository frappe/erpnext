// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["BOM Stock Analysis"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "bom",
			label: __("BOM"),
			fieldtype: "Link",
			options: "BOM",
			reqd: 1,
			get_query: function () {
				let company = frappe.query_report.get_filter_value("company");
				return {
					filters: company ? { company } : {},
				};
			},
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "MultiSelectList",
			options: "Warehouse",
			get_data: function (txt) {
				let company = frappe.query_report.get_filter_value("company");
				return frappe.db.get_link_options("Warehouse", txt, company ? { company } : {});
			},
		},
		{
			fieldname: "qty_to_make",
			label: __("FG Items to Make"),
			fieldtype: "Float",
		},
		{
			fieldname: "show_exploded_view",
			label: __("Show availability of exploded items"),
			fieldtype: "Check",
			default: false,
		},
	],
	formatter(value, row, column, data, default_formatter) {
		if (data && data.bold && column.fieldname === "item") {
			return value ? `<b>${value}</b>` : "";
		}

		value = default_formatter(value, row, column, data);

		if (column.fieldname === "difference_qty" && value !== "" && value !== undefined) {
			const numeric = parseFloat(value.replace(/,/g, "")) || 0;
			if (numeric < 0) {
				value = `<span style="color: red">${value}</span>`;
			} else if (numeric > 0) {
				value = `<span style="color: green">${value}</span>`;
			}
		}

		if (data && data.bold) {
			if (column.fieldname === "description") {
				const qty_to_make = Number(frappe.query_report.get_filter_value("qty_to_make")) || 0;
				const producible = Number(String(data.description ?? "").replace(/,/g, "")) || 0;
				const colour = qty_to_make && producible < qty_to_make ? "red" : "green";
				return `<b style="color: ${colour}">${value}</b>`;
			}
			return `<b>${value}</b>`;
		}

		return value;
	},
};
