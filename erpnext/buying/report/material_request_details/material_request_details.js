// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Material Request Details"] = {
	"filters": [
		{
			fieldname: "naming_series",
			label: __("Material Request"),
			fieldtype: "Link",
			options: "Material Request",
			reqd: 1,
			get_query: () => {
			var company = frappe.query_report.get_filter_value('docstatus');
			return {
			filters: {
			'docstatus': 1
			}
			}
			}
			},
	]
};
