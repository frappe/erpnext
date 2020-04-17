// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Sales Book"] = {
	"filters": [
		{
			fieldname:"company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1
		},
		{
			fieldname:"branch_office",
			label: __("Branch Office"),
			fieldtype: "Link",
			options: "GSucursal",
		},
		{
			fieldname:"cashier",
			label: __("Cashier"),
			fieldtype: "Link",
			options: "GPos",
		},
		{
			fieldname:"type_document",
			label: __("Type Document"),
			fieldtype: "Link",
			options: "GType Document",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1
		},
	]
};
