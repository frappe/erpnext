// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["UAE VAT Register"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "doc_type",
			label: __("Document Type"),
			fieldtype: "Select",
			options: ["Sales Invoice", "Purchase Invoice"],
			default: "Sales Invoice",
			reqd: 1,
		},
		{
			fieldname: "category",
			label: __("Category"),
			fieldtype: "Select",
			options: ["", "Standard", "Zero Rated", "Exempt Rated"],
			depends_on: "eval: doc.doc_type == 'Sales Invoice'",
		},
		{
			fieldname: "vat",
			label: __("Emirate"),
			fieldtype: "Select",
			options: [
				"",
				"Abu Dhabi",
				"Dubai",
				"Sharjah",
				"Ajman",
				"Umm Al Quwain",
				"Ras Al Khaimah",
				"Fujairah",
			],
			depends_on: "eval: doc.doc_type == 'Sales Invoice'",
		},
		{
			fieldname: "reverse_charge",
			label: __("Reverse Charge"),
			fieldtype: "Select",
			options: ["", "Y", "N"],
			depends_on: "eval: doc.doc_type == 'Purchase Invoice'",
		},
		{
			fieldname: "item_wise",
			label: __("Item-wise"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
