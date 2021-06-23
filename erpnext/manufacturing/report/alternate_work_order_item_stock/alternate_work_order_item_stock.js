// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Alternate Work Order Item Stock"] = {
	"filters": [
		{
			fieldname: "name",
			label: __("Work order"),
			fieldtype: "Link",
			options:"Work Order",
			default: "",
			reqd: 0
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options:"Item",
			default: "",
			reqd: 0
		}
	]
};
