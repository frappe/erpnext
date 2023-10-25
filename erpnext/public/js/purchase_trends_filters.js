// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

erpnext.get_purchase_trends_filters = function() {
	return [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"period",
			"label": __("Period"),
			"fieldtype": "Select",
			"options": [
				{ "value": "Monthly", "label": __("Monthly") },
				{ "value": "Quarterly", "label": __("Quarterly") },
				{ "value": "Half-Yearly", "label": __("Half-Yearly") },
				{ "value": "Yearly", "label": __("Yearly") }
			],
			"default": "Monthly"
		},
		{
			"fieldname":"fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options":'Fiscal Year',
			"default": erpnext.utils.get_fiscal_year(frappe.datetime.get_today())
		},
		{
			"fieldname":"period_based_on",
			"label": __("Period based On"),
			"fieldtype": "Select",
			"options": [
				{ "value": "posting_date", "label": __("Posting Date") },
				{ "value": "bill_date", "label": __("Billing Date") },
			],
			"default": "posting_date"
		},
		{
			"fieldname":"based_on",
			"label": __("Based On"),
			"fieldtype": "Select",
			"options": [
				{ "value": "Item", "label": __("Item") },
				{ "value": "Item Group", "label": __("Item Group") },
				{ "value": "Supplier", "label": __("Supplier") },
				{ "value": "Supplier Group", "label": __("Supplier Group") },
				{ "value": "Project", "label": __("Project") }
			],
			"default": "Item",
			"dashboard_config": {
				"read_only": 1
			}
		},
		{
			"fieldname":"group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": [
				"",
				{ "value": "Item", "label": __("Item") },
				{ "value": "Supplier", "label": __("Supplier") }
			],
			"default": ""
		},
	];
}
