// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Student Batch-Wise Attendance"] = {
	"filters": [{
		"fieldname": "date",
		"label": __("Date"),
		"fieldtype": "Date",
		"default": frappe.datetime.get_today(),
		"reqd": 1
	}]
}