// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["GSTR-1"] = {
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
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -3),
			"width": "80"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "type_of_business",
			"label": __("Type of Business"),
			"fieldtype": "Select",
			"reqd": 1,
			"options": ["B2B", "B2C Large", "B2C Small", "CDNR", "EXPORT"],
			"default": "B2B"
		}
	],
	onload: function (report) {

		report.page.add_inner_button(__("Download as JSON"), function () {
			var filters = report.get_values();

			frappe.call({
				method: 'erpnext.regional.report.gstr_1.gstr_1.get_json',
				args: {
					data: report.data,
					report_name: report.report_name,
					filters: filters
				},
				callback: function(r) {
					if (r.message) {
						const args = {
							cmd: 'erpnext.regional.report.gstr_1.gstr_1.download_json_file',
							data: r.message.data,
							report_name: r.message.report_name,
							report_type: r.message.report_type
						};
						open_url_post(frappe.request.url, args);
					}
				}
			});
		});
	}
}
