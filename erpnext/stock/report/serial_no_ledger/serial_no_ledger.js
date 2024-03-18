// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Serial No Ledger"] = {
	filters: [
		{
			label: __("Item Code"),
			fieldtype: "Link",
			fieldname: "item_code",
			reqd: 1,
			options: "Item",
			get_query: function () {
				return {
					filters: {
						has_serial_no: 1,
					},
				};
			},
		},
		{
			label: __("Warehouse"),
			fieldtype: "Link",
			fieldname: "warehouse",
			options: "Warehouse",
			get_query: function () {
				let company = frappe.query_report.get_filter_value("company");

				if (company) {
					return {
						filters: {
							company: company,
						},
					};
				}
			},
		},
		{
			label: __("Serial No"),
			fieldtype: "Link",
			fieldname: "serial_no",
			options: "Serial No",
			get_query: function () {
				let item_code = frappe.query_report.get_filter_value("item_code");
				let warehouse = frappe.query_report.get_filter_value("warehouse");

				let query_filters = { item_code: item_code };
				if (warehouse) {
					query_filters["warehouse"] = warehouse;
				}

				return {
					filters: query_filters,
				};
			},
		},
		{
			label: __("As On Date"),
			fieldtype: "Date",
			fieldname: "posting_date",
			default: frappe.datetime.get_today(),
		},
		{
			label: __("Posting Time"),
			fieldtype: "Time",
			fieldname: "posting_time",
			default: frappe.datetime.get_time(),
		},
	],
};
