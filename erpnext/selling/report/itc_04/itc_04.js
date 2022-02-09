// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["ITC-04"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "company_address",
			"label": __("Address"),
			"fieldtype": "Link",
			"options": "Address",
			"get_query": function () {
				var company = frappe.query_report.get_filter_value('company');
				if (company) {
					return {
						"query": 'frappe.contacts.doctype.address.address.address_query',
						"filters": { link_doctype: 'Company', link_name: company }
					};
				}
			}
		},
		{
			"fieldname":"fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options":"Fiscal Year",
			"reqd": 1
		},
		{
			"fieldname":"q_return",
			"label": __("Return"),
			"fieldtype": "Select",
			// "options": ['Apr-Jun','July-Sept','Oct-Dec','Jan-March', 'First Half', 'Second Half'],
			"options": ['Apr-Sept', 'Oct-March'],
			"reqd": 1
		},
		{
				"label": "Report",
				"fieldname": "report",
				"fieldtype": "Select",
				"reqd": 1,
				"default": "ITC-04",
				"options": ["ITC-04", "ITC-05 A", "ITC-05 B", "ITC-05 C"]
		},
	],

	onload: function (report) {

		report.page.add_inner_button(__("Download as JSON"), function () {
			var filters = report.get_values();

			frappe.call({
				method: 'erpnext.selling.report.itc_04.itc_04.get_json',
				args: {
					data: report.data,
					report_name: report.report_name,
					filters: filters
				},
				callback: function(r) {
					if (r.message) {
						const args = {
							cmd: 'erpnext.selling.report.itc_04.itc_04.download_json_file',
							data: r.message.data,
							report_name: r.message.report_name,
							report: r.message.report
						};
						open_url_post(frappe.request.url, args);
					}
				}
			});
		});
	}
};
