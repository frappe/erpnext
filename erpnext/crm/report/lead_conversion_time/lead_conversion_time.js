// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
<<<<<<< HEAD
/* eslint-disable */
=======
>>>>>>> ec74a5e566 (style: format js files)

frappe.query_reports["Lead Conversion Time"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_days(frappe.datetime.nowdate(), -30),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.nowdate(),
		},
	],
};
