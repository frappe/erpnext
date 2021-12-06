// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Lost Opportunity"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -12),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"lost_reason",
			"label": __("Lost Reason"),
			"fieldtype": "Link",
			"options": "Opportunity Lost Reason"
		},
		{
			"fieldname":"territory",
			"label": __("Territory"),
			"fieldtype": "Link",
			"options": "Territory"
		},
		{
			"fieldname":"opportunity_from",
			"label": __("Opportunity From"),
			"fieldtype": "Link",
			"options": "DocType",
			"get_query": function() {
				return {
					"filters": {
						"name": ["in", ["Customer", "Lead"]],
					}
				}
			}
		},
		{
			"fieldname":"party_name",
			"label": __("Party"),
			"fieldtype": "Dynamic Link",
			"options": "opportunity_from"
		},
		{
			"fieldname":"contact_by",
			"label": __("Next Contact By"),
			"fieldtype": "Link",
			"options": "User"
		},
	]
};
