// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Attendance"] = {
	"filters": [{
        "fieldname":"employee",
		"label": __("Employee"),
		"fieldtype": "Link",
		"options": "Employee"
    },
    {
        "fieldname": "year",
        "label": __("Year"),
        "fieldtype": "Select",
        "reqd": 1,
        "options": "\n2016\n2017\n2018\n2019\n2020",
		"default": '2017',
    },
    {
        "fieldname": "month",
        "label": __("Month"),
        "fieldtype": "Select",
        "reqd": 1,
        "options": "Jan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
		"default": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
				"Dec"][frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()],
    },
    ]
}
