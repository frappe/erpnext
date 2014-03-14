// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Sales Person-wise Transaction Summary"] = {
	"filters": [
		{
			fieldname: "sales_person",
			label: frappe._("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person"
		},
		{
			fieldname: "doc_type",
			label: frappe._("Document Type"),
			fieldtype: "Select",
			options: "Sales Order\nDelivery Note\nSales Invoice",
			default: "Sales Order"
		},
		{
			fieldname: "from_date",
			label: frappe._("From Date"),
			fieldtype: "Date",
			default: frappe.defaults.get_user_default("year_start_date"),
		},
		{
			fieldname:"to_date",
			label: frappe._("To Date"),
			fieldtype: "Date",
			default: get_today()
		},
		{
			fieldname:"company",
			label: frappe._("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("company")
		},
		{
			fieldname:"item_group",
			label: frappe._("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname:"brand",
			label: frappe._("Brand"),
			fieldtype: "Link",
			options: "Brand",
		},
		{
			fieldname:"customer",
			label: frappe._("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname:"territory",
			label: frappe._("Territory"),
			fieldtype: "Link",
			options: "Territory",
		},
	]
}