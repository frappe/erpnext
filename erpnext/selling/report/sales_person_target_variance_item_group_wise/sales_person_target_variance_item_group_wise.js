// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Sales Person Target Variance Item Group-Wise"] = {
	"filters": [
		{
			fieldname: "fiscal_year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: sys_defaults.fiscal_year
		},
		{
			fieldname: "period",
			label: __("Period"),
			fieldtype: "Select",
			options: "Monthly\nQuarterly\nHalf-Yearly\nYearly",
			default: "Monthly"
		},
		{
			fieldname: "target_on",
			label: __("Target On"),
			fieldtype: "Select",
			options: "Quantity\nAmount",
			default: "Quantity"
		},
	]
}