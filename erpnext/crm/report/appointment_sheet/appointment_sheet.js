// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Appointment Sheet"] = {
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
			fieldname:"from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			on_change: function() {
				var from_date = frappe.query_report.get_filter_value('from_date');
				var to_date = frappe.query_report.get_filter_value('to_date');
				if (from_date && to_date) {
					if (frappe.datetime.str_to_obj(from_date) > frappe.datetime.str_to_obj(to_date)) {
						frappe.query_report.set_filter_value('to_date', from_date);
					}
				}
			}
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "appointment_type",
			label: __("Appointment Type"),
			fieldtype: "Link",
			options: "Appointment Type",
		},
	],
	onChange: function(new_value, column, data, rowIndex) {
		if (column.fieldname == "remarks") {
			return frappe.call({
				method: "frappe.client.set_value",
				args: {
					doctype: "Appointment",
					name: data.appointment,
					fieldname: 'remarks',
					value: new_value
				}
			});
		}
	}
};
