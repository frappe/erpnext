// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Email Summary"] = {
	"filters": [
		{
			fieldname: "reference_document_type",
			label: __("Reference Document Type"),
			fieldtype: "Link",
			options: "DocType",
			default: "Lead"
		},
		{
			fieldname: "reference_document_name",
			label: __("Reference Document Name"),
			fieldtype: "Dynamic Link",
			options: "reference_document_type"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -12)
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today()
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default('company')
		},
		{
			fieldname: "frequency",
			label: __("Frequency"),
			fieldtype: "Select",
			options: [
				"Monthly",
				"Quarterly",
				"Half-Yearly",
				"Yearly"
			],
			default: "Monthly"
		},
		{
			fieldname: "type",
			label: __("Type"),
			fieldtype: "Select",
			options: [
				"",
				"Sent",
				"Received"
			],
			default: ""
		},
		{
			fieldname: "email_template_used",
			label: __("Email Template Used"),
			fieldtype: "Check",
			default: 0
		},
	]
};
