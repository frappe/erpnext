// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Downtime Analysis"] = {
	filters: [
		{
			label: __("From Date"),
			fieldname: "from_date",
			fieldtype: "Datetime",
			default: frappe.datetime.convert_to_system_tz(
				frappe.datetime.add_months(frappe.datetime.now_datetime(), -1)
			),
			reqd: 1,
		},
		{
			label: __("To Date"),
			fieldname: "to_date",
			fieldtype: "Datetime",
			default: frappe.datetime.now_datetime(),
			reqd: 1,
		},
		{
			label: __("Machine"),
			fieldname: "workstation",
			fieldtype: "Link",
			options: "Workstation",
		},
	],
};
