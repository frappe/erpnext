// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
<<<<<<< HEAD
/* eslint-disable */
=======
>>>>>>> ec74a5e566 (style: format js files)

frappe.query_reports["Support Hour Distribution"] = {
	filters: [
		{
			lable: __("From Date"),
			fieldname: "from_date",
			fieldtype: "Date",
			default: frappe.datetime.nowdate(),
			reqd: 1,
		},
		{
			lable: __("To Date"),
			fieldname: "to_date",
			fieldtype: "Date",
			default: frappe.datetime.nowdate(),
			reqd: 1,
		},
	],
};
