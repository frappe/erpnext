// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Call Log Summary"] = {
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
				"Quarterly"
			],
			default: "Monthly"
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "MultiSelectList",
			get_data: function() {
				return [
					{value: "Completed", description: "Status"},
					{value: "Failed", description: "Status"},
					{value: "Busy", description: "Status"},
					{value: "No Answer", description: "Status"},
					{value: "Canceled", description: "Status"}
				]
			}
		},
		{
			fieldname: "type",
			label: __("Type"),
			fieldtype: "Select",
			options: [
				"",
				"Incoming",
				"Outgoing"
			],
			default: ""
		},
	]
};
