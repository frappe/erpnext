// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Support Hours"] = {
	"filters": [
		{
			'lable': __("From Date"),
			'fieldname': 'from_date',
			'fieldtype': 'Date',
			'default': frappe.datetime.nowdate(),
			'reqd': 1
		},
		{
			'lable': __("To Date"),
			'fieldname': 'to_date',
			'fieldtype': 'Date',
			'default': frappe.datetime.nowdate(),
			'reqd': 1
		}
	],
	get_chart_data: function(columns, result) {
		return {
			data: {
				x: 'Date',
				columns: [
					['Date'].concat($.map(result, function(d) { return d.date; })),
					[columns[3].label].concat($.map(result, function(d) { return d[columns[3].label]; })),
					[columns[4].label].concat($.map(result, function(d) { return d[columns[4].label]; })),
					[columns[5].label].concat($.map(result, function(d) { return d[columns[5].label]; })),
					[columns[6].label].concat($.map(result, function(d) { return d[columns[6].label]; })),
					[columns[7].label].concat($.map(result, function(d) { return d[columns[7].label]; }))
				]
			},
			chart_type: 'bar',

		}
	}
}
