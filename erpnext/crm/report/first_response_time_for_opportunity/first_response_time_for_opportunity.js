// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["First Response Time for Opportunity"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.add_days(frappe.datetime.nowdate(), -30)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.nowdate()
		},
	],
	get_chart_data: function (_columns, result) {
		return {
			data: {
				labels: result.map(d => d[0]),
				datasets: [{
					name: "First Response Time",
					values: result.map(d => d[1])
				}]
			},
			type: "line",
			tooltipOptions: {
				formatTooltipY: d => {
					let duration_options = {
						hide_days: 0,
						hide_seconds: 0
					};
					value = frappe.utils.get_formatted_duration(d, duration_options);
					return value;
				}
			}
		}
	}
};
