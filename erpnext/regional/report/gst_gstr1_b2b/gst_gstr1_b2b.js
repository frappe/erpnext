// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["GST GSTR1 B2B"] = {
	"filters": [

			{
				"fieldname":"from_date",
				"label": __("From Date"),
				"fieldtype": "Date",
				"default": frappe.datetime.month_start(frappe.datetime.get_today()),
				"width": "80"
			},
			{
				"fieldname":"to_date",
				"label": __("To Date"),
				"fieldtype": "Date",
				"default": frappe.datetime.month_end(get_today())
			},

			
			{
				"fieldname":"company",
				"label": __("Company"),
				"fieldtype": "Link",
				"options": "Company",
				"default": frappe.defaults.get_user_default("Company")
			},

			{
				"fieldname":"igst",
				"label":__("IGST"),
				"fieldtype":"Link",
				"options":"Account"
			},
			{
				"fieldname":"sgst",
				"label":__("SGST"),
				"fieldtype":"Link",
				"options":"Account"
			},
			{
				"fieldname":"cgst",
				"label":__("CGST"),
				"fieldtype":"Link",
				"options":"Account"
			},
			{
				"fieldname":"cess",
				"label":__("Cess"),
				"fieldtype":"Link",
				"options":"Account"
			}


	]
}
