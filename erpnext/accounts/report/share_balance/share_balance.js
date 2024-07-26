// -*- coding: utf-8 -*-
// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Share Balance"] = {
	filters: [
		{
			fieldname: "date",
			label: __("Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "shareholder",
			label: __("Shareholder"),
			fieldtype: "Link",
			options: "Shareholder",
		},
	],
};
