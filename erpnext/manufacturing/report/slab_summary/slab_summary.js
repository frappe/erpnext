// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Slab Summary"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start()
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end()
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
			get_query: function () {
				return {
					filters: {
						"item_group": "Finished Goods"
					}
				};
			}
		}
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "item_code" && data && data.item_code) {
			return `<a href="#" class="slab-summary-item-link" data-item-code="${frappe.utils.escape_html(data.item_code)}">${value}</a>`;
		}
		return value;
	},

	onload: function (report) {
		report.page.wrapper.on("click", ".slab-summary-item-link", function (e) {
			e.preventDefault();

			const item_code = $(this).attr("data-item-code");
			const from_date = report.get_filter_value("from_date");
			const to_date = report.get_filter_value("to_date");

			frappe.set_route("query-report", "Slab Detail", {
				from_date: from_date,
				to_date: to_date,
				item_code: item_code
			});
		});
	}
};