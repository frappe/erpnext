// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Purchase order for category purchase"] = {
	"filters": [
		{
			fieldname:"category_purchase",
			label: __("Category For Purchase"),
			fieldtype: "Link",
			options: "Category for purchase",
			reqd: 1
		},
	]
};
