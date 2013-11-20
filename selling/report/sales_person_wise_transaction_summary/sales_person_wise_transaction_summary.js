// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Sales Person-wise Transaction Summary"] = {
	"filters": [
		{
			fieldname: "sales_person",
			label: wn._("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person"
		},
		{
			fieldname: "doc_type",
			label: wn._("Document Type"),
			fieldtype: "Select",
			options: "Sales Order\nDelivery Note\nSales Invoice",
			default: "Sales Order"
		},
		{
			fieldname: "from_date",
			label: wn._("From Date"),
			fieldtype: "Date",
			default: wn.defaults.get_user_default("year_start_date"),
		},
		{
			fieldname:"to_date",
			label: wn._("To Date"),
			fieldtype: "Date",
			default: get_today()
		},
		{
			fieldname:"company",
			label: wn._("Company"),
			fieldtype: "Link",
			options: "Company",
			default: wn.defaults.get_default("company")
		},
		{
			fieldname:"item_group",
			label: wn._("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname:"brand",
			label: wn._("Brand"),
			fieldtype: "Link",
			options: "Brand",
		},
		{
			fieldname:"customer",
			label: wn._("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname:"territory",
			label: wn._("Territory"),
			fieldtype: "Link",
			options: "Territory",
		},
	]
}