// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["LC Costing"] = {
	filters: [
		{
			fieldname: "landed_cost_voucher",
			label: __("Landed Cost Voucher"),
			fieldtype: "Link",
			options: "Landed Cost Voucher",
			filters: {
				docstatus: ['<', 2]
			}
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_start_date"),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_end_date"),
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "reference_price_list",
			label: __("Reference Price List"),
			fieldtype: "Link",
			options: "Price List",
		},
	],
	onChange: function(new_value, column, data, rowIndex) {
		var method;
		var args;

		if (column.fieldname === "reference_rate" && column.price_list) {
			method = "erpnext.stock.report.item_prices.item_prices.set_item_pl_rate";
			args = {
				effective_date: data['posting_date'],
				item_code: data['item_code'],
				price_list: column.price_list,
				price_list_rate: new_value,
				uom: data['uom']
			};
		}

		if (method) {
			return frappe.call({
				method: method,
				args: args,
			});
		}
	}
};
