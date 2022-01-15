// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["ITC-04"] = {
	"filters": [
		{
			fieldname: "gstin_of_manufacturer",
			label: __("GSTIN of Manufacturer"),
			fieldtype: "Data",
			default: "",
			reqd: 0
		},
		{
			"fieldname":"from_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.nowdate(), -12),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("End Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.nowdate(),
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
