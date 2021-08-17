// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Month wise Purchase VAT Register"] = {
	"filters": [
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Data",
			default: "",
			reqd: 0
		},
		{
		fieldname: "company",
		label: __("Company"),
		fieldtype: "Link",
		options:"Company",
		reqd: 0
		},
	]
};