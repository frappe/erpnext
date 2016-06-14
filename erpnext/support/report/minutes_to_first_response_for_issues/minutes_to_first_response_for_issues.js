frappe.query_reports["Minutes to First Response for Issues"] = {
    "filters": [
        {
            "fieldname":"from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
			'reqd': 1,
            "default": frappe.datetime.add_days(frappe.datetime.nowdate(), -30)
        },
        {
            "fieldname":"to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
			'reqd': 1,
            "default":frappe.datetime.nowdate()
        },
    ],
	get_chart_data: function(columns, result) {
		console.log(result);
		return {
			data: {
				x: 'Date',
				columns: [
					['Date'].concat($.map(result, function(d) { return d[0]; })),
					['Mins to first reponse'].concat($.map(result, function(d) { return d[1]; }))
				]
			},
			chart_type: 'line'
		}
	}
}
