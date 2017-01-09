// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Daily Timesheet Summary"] = {
	"filters": [
		{
			"fieldname":"date",
			"label": __("Date"),
			"fieldtype": "DateRange",
			"start_with_value": true,
			"default_from":frappe.datetime.get_today(),
			"default_to":frappe.datetime.get_today(),
		},
	]
}
