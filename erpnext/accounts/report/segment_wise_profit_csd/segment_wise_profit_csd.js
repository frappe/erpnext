// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Segment Wise Profit CSD"] = {
	"filters": [
		{
			fieldname:"from_date",
			reqd: 1,
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			
		},
		{
			fieldname:"to_date",
			reqd: 1,
			default: frappe.datetime.month_end(),
			label: __("To Date"),
			fieldtype: "Date",
		},				
		{
			fieldname:"company",
			reqd: 1,
			label: __("Company"),
			fieldtype: "Select",
			options: ["Unit 5", "Unit 8", "Unit 11"]
		}

	]
};
