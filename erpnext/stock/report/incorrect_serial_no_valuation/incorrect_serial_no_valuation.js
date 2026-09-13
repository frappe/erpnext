// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Incorrect Serial No Valuation"] = {
	formatter(value, row, column, data, default_formatter) {
		value = erpnext.utils.format_serial_batch_number(value, row, column, data, default_formatter);
		if (column.serial_batch && data?.total_label) {
			return `<strong>${value}</strong>`;
		}
		return value;
	},
	filters: [
		{
			label: __("Item Code"),
			fieldtype: "Link",
			fieldname: "item_code",
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
			label: __("From Date"),
			fieldtype: "Date",
			fieldname: "from_date",
			reqd: 1,
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
		},
		{
			label: __("To Date"),
			fieldtype: "Date",
			fieldname: "to_date",
			reqd: 1,
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
		},
	],
};
