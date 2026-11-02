// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Sales Order Trends"] = {
	filters: [
		...erpnext.sales_trends_filters.filters,
		{
			fieldname: "include_closed_orders",
			label: __("Include Closed Orders"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
