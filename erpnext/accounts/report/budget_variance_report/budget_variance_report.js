// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.query_reports["Budget Variance Report"] = {
	"filters": [
		{
			fieldname: "fiscal_year",
			label: wn._("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: sys_defaults.fiscal_year
		},
		{
			fieldname: "period",
			label: wn._("Period"),
			fieldtype: "Select",
			options: "Monthly\nQuarterly\nHalf-Yearly\nYearly",
			default: "Monthly"
		},
		{
			fieldname: "company",
			label: wn._("Company"),
			fieldtype: "Link",
			options: "Company",
			default: wn.defaults.get_default("company")
		},
	]
}