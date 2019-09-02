// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["FBR Sales Tax Report"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1
		},
		{
			fieldname: "party",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "for_export",
			label: __("For Export"),
			fieldtype: "Check",
		},
	],
	onChange: function(new_value, column, data, rowIndex) {
		if (column.fieldname == "state" && new_value) {
			if (!data.address_name) {
				frappe.throw(__("No address set in Sales Invoice {0}", data.invoice))
			}

			return frappe.call({
				method: "frappe.client.set_value",
				args: {
					doctype: "Address",
					name: data.address_name,
					fieldname: 'state',
					value: new_value
				},
				callback: function (r) {
					frappe.query_report.refresh();
				}
			});
		}
	}
};
