// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Item-wise Purchase History By Purchase Justification"] = {
	"filters": [
		{
			fieldname: "purchase_justification",
			label: __("Purchase Justification"),
			fieldtype: "Link",
			options: "Purchase Justification",
			reqd: 1
		},
	]
};
