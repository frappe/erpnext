// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
<<<<<<< HEAD
/* eslint-disable */
=======
>>>>>>> ec74a5e566 (style: format js files)

frappe.query_reports["Production Analytics"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
<<<<<<< HEAD
			default: frappe.defaults.get_user_default("year_start_date"),
			reqd: 1
=======
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			reqd: 1,
>>>>>>> ec74a5e566 (style: format js files)
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
<<<<<<< HEAD
			default: frappe.defaults.get_user_default("year_end_date"),
			reqd: 1
=======
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
			reqd: 1,
>>>>>>> ec74a5e566 (style: format js files)
		},
		{
			fieldname: "range",
			label: __("Range"),
			fieldtype: "Select",
			options: [
				{ value: "Weekly", label: __("Weekly") },
				{ value: "Monthly", label: __("Monthly") },
				{ value: "Quarterly", label: __("Quarterly") },
				{ value: "Yearly", label: __("Yearly") },
			],
			default: "Monthly",
			reqd: 1,
		},
	],
};
