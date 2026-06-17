// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Purchase Person Commission Summary"] = {
	filters: [
		{
			fieldname: "purchase_person",
			label: __("Purchase Person"),
			fieldtype: "Link",
			options: "Purchase Person",
		},
		{
			fieldname: "doc_type",
			label: __("Document Type"),
			fieldtype: "Select",
			options: "Purchase Order\nPurchase Receipt\nPurchase Invoice",
			default: "Purchase Order",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
		},
	],
};
