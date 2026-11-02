// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Purchase Invoice Trends"] = {
	filters: [
		...erpnext.purchase_trends_filters.filters,
		{
			fieldname: "period_based_on",
			label: __("Period based On"),
			fieldtype: "Select",
			options: [
				{ value: "posting_date", label: __("Posting Date") },
				{ value: "bill_date", label: __("Billing Date") },
			],
			default: "posting_date",
		},
	],
};
