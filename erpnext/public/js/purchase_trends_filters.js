// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

var get_filters = function(){
	return [
		{
			"fieldname":"period",
			"label": frappe._("Period"),
			"fieldtype": "Select",
			"options": ["Monthly", "Quarterly", "Half-Yearly", "Yearly"].join("\n"),
			"default": "Monthly"
		},
		{
			"fieldname":"based_on",
			"label": frappe._("Based On"),
			"fieldtype": "Select",
			"options": ["Item", "Item Group", "Supplier", "Supplier Type", "Project"].join("\n"),
			"default": "Item"
		},
		{
			"fieldname":"group_by",
			"label": frappe._("Group By"),
			"fieldtype": "Select",
			"options": ["Item", "Supplier"].join("\n"),
			"default": ""
		},
		{
			"fieldname":"fiscal_year",
			"label": frappe._("Fiscal Year"),
			"fieldtype": "Link",
			"options":'Fiscal Year',
			"default": sys_defaults.fiscal_year
		},
		{
			"fieldname":"company",
			"label": frappe._("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("company")
		},
	];
}