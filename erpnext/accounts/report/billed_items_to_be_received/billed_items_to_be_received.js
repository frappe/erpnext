// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
<<<<<<< HEAD
/* eslint-disable */

frappe.query_reports['Billed Items To Be Received'] = {
	'filters': [
=======

frappe.query_reports["Billed Items To Be Received"] = {
	filters: [
>>>>>>> ec74a5e566 (style: format js files)
		{
			label: __("Company"),
			fieldname: "company",
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_default("Company"),
		},
		{
<<<<<<< HEAD
			'label': __('As on Date'),
			'fieldname': 'posting_date',
			'fieldtype': 'Date',
			'reqd': 1,
			'default': get_today()
=======
			label: __("As on Date"),
			fieldname: "posting_date",
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
>>>>>>> ec74a5e566 (style: format js files)
		},
		{
			label: __("Purchase Invoice"),
			fieldname: "purchase_invoice",
			fieldtype: "Link",
			options: "Purchase Invoice",
		},
	],
};
