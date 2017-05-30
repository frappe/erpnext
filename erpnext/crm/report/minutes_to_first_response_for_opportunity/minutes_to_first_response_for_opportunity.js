// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Minutes to First Response for Opportunity"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			'reqd': 1,
			"default": frappe.datetime.add_days(frappe.datetime.nowdate(), -30)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			'reqd': 1,
			"default": frappe.datetime.nowdate()
		},
	],
	get_chart_data: function (columns, result) {
		return {
			data: {
				x: 'Date',
				columns: [
					['Date'].concat($.map(result, function (d) { return d[0]; })),
					['Mins to first response'].concat($.map(result, function (d) { return d[1]; }))
				]
				// rows: [['Date', 'Mins to first response']].concat(result)
			},
			axis: {
				x: {
					type: 'timeseries',
					tick: {
						format: frappe.ui.py_date_format
					}
				}
			},
			chart_type: 'line',

		}
	}
}
