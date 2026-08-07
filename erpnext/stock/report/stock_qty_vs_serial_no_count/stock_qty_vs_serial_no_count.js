// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Qty vs Serial No Count"] = {
	onload: function (report) {
		report.page.add_inner_button(__("Sync Serial No Status"), () => {
			const warehouse = report.get_filter_value("warehouse");
			if (!warehouse) {
				frappe.msgprint(__("Please select a warehouse first."));
				return;
			}

			frappe.confirm(
				__(
					"This will update the warehouse and status of Serial Nos counted in {0} to match the stock ledger. Continue?",
					[warehouse.bold()]
				),
				() => {
					frappe.call({
						method: "erpnext.stock.report.stock_qty_vs_serial_no_count.stock_qty_vs_serial_no_count.sync_serial_no_status",
						args: { warehouse: warehouse },
						freeze: true,
					});
				}
			);
		});
	},

	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: function () {
				const company = frappe.query_report.get_filter_value("company");
				return {
					filters: { company: company },
				};
			},
			reqd: 1,
		},
		{
			fieldname: "show_disabled_items",
			label: __("Show Disabled Items"),
			fieldtype: "Check",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname == "difference" && data) {
			if (data.difference > 0) {
				value = "<span style='color:red'>" + value + "</span>";
			} else if (data.difference < 0) {
				value = "<span style='color:red'>" + value + "</span>";
			}
		}
		return value;
	},
};
