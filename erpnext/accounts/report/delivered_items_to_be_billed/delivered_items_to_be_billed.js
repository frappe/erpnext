// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Delivered Items To Be Billed"] = {
<<<<<<< HEAD
	filters: [
		{
			label: __("Company"),
			fieldname: "company",
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_default("Company"),
		},
		{
			label: __("As on Date"),
			fieldname: "posting_date",
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			label: __("Delivery Note"),
			fieldname: "delivery_note",
			fieldtype: "Link",
			options: "Delivery Note",
		},
	],
=======
	filters: [],
>>>>>>> 7c4cf3e834 (Favicon.svg)
};
