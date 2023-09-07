// Copyright (c) 2023, viral patel and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Timesheet Billing Summary"] = {
	"filters": [
		{
			fieldname:"from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.month_start(), -1),
			reqd: 1
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.month_start(),-1),
			reqd: 1
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
			
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			
		},
		{
			fieldname:"include_draft_timesheets",
			label: __("Show Draft Timesheets"),
			fieldtype: "Check",
		},
		{
			fieldname:"show_timesheet_detail",
			label: __("Show Detailed Timesheets"),
			fieldtype: "Check",
		},

	]
};
