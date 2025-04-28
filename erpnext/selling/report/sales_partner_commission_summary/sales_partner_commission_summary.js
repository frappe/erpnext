// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Partner Commission Summary"] = {
	filters: [
		{
<<<<<<< HEAD
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
			fieldname: "sales_partner",
			label: __("Sales Partner"),
			fieldtype: "Link",
			options: "Sales Partner",
		},
		{
			fieldname: "doctype",
			label: __("Document Type"),
			fieldtype: "Select",
<<<<<<< HEAD
			options: "Sales Order\nDelivery Note\nSales Invoice\nPOS Invoice",
=======
			options: "Sales Order\nDelivery Note\nSales Invoice",
>>>>>>> 7c4cf3e834 (Favicon.svg)
			default: "Sales Order",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
<<<<<<< HEAD
=======
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
>>>>>>> 7c4cf3e834 (Favicon.svg)
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "territory",
			label: __("Territory"),
			fieldtype: "Link",
			options: "Territory",
		},
	],
};
