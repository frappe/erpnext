// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Budget Variance Report"] = {
	"filters": [
		{
			fieldname: "fiscal_year",
			label: frappe._("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: sys_defaults.fiscal_year
		},
		{
			fieldname: "period",
			label: frappe._("Period"),
			fieldtype: "Select",
			options: "Monthly\nQuarterly\nHalf-Yearly\nYearly",
			default: "Monthly"
		},
		{
			fieldname: "company",
			label: frappe._("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("company")
		},
	]
}