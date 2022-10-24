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
						return frappe.query_report.set_filter_value('to_date', from_date);
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

	formatter: function(value, row, column, data, default_formatter) {
		var style = {};
		var link;

		if (column.fieldname == 'reminder') {
			if (data.last_sent_dt) {
				style['color'] = 'green';
			} else if (data.scheduled_reminder_dt) {
				style['color'] = 'blue';
			}
		}

		if (column.fieldname == 'status') {
			if (frappe.listview_settings['Appointment']) {
				var indicator = frappe.listview_settings['Appointment'].get_indicator(data);
				if (indicator) {
					var indicator_color = indicator[1];
					return `<span class="indicator ${indicator_color}"><span>${data.status}</span></span>`;
				}
			}
		}

		return default_formatter(value, row, column, data, {css: style, link_href: link, link_target: "_blank"});
	},

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
