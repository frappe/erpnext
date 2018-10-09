// Copyright (c) 2016, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Eway Bill"] = {
	"filters": [
		{
			'fieldname': 'doc_name',
			'label': __("Doc Name"),
			'fieldtype': 'Dynamic Link',
			"get_options": function() {
				let doc_type = frappe.query_report.get_values().doc_type;
				if(!doc_type) {
					frappe.throw(__("Please select Doc Type first"));
				}
				return doc_type;
			}
		},
		{
			'fieldname': 'posting_date',
			'label': __("Date"),
			'fieldtype': 'DateRange',
			'default': [frappe.datetime.nowdate(), frappe.datetime.nowdate()]
		},
		{
			'fieldname': 'customer',
			'label': __("Customer"),
			'fieldtype': 'Link',
			'options': 'Customer'
		},
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			'fieldname': 'doc_type',
			'label': __("Doc Type"),
			'fieldtype': 'Select',
			'options': "Delivery Note\nSales Invoice",
			'default': "Delivery Note"
		}
	]
}
