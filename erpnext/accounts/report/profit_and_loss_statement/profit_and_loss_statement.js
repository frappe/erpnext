// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Profit and Loss Statement"] = $.extend({},
		erpnext.financial_statements);

	frappe.query_reports["Profit and Loss Statement"]["filters"].push(
		{
			"fieldname":"cost_center",
			"label": __("Cost Center"),
			"fieldtype": "MultiSelect",
			get_data: function() {
				var cost_centers = frappe.query_report.get_filter_value("cost_center") || "";

				const values = cost_centers.split(/\s*,\s*/).filter(d => d);
				const txt = cost_centers.match(/[^,\s*]*$/)[0] || '';
				let data = [];

				frappe.call({
					type: "GET",
					method:'frappe.desk.search.search_link',
					async: false,
					no_spinner: true,
					args: {
						doctype: "Cost Center",
						txt: txt,
						filters: {
							"company": frappe.query_report.get_filter_value("company"),
							"name": ["not in", values]
						}
					},
					callback: function(r) {
						data = r.results;
					}
				});
				return data;
			}
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "MultiSelect",
			get_data: function() {
				var projects = frappe.query_report.get_filter_value("project") || "";

				const values = projects.split(/\s*,\s*/).filter(d => d);
				const txt = projects.match(/[^,\s*]*$/)[0] || '';
				let data = [];

				frappe.call({
					type: "GET",
					method:'frappe.desk.search.search_link',
					async: false,
					no_spinner: true,
					args: {
						doctype: "Project",
						txt: txt,
						filters: {
							"name": ["not in", values]
						}
					},
					callback: function(r) {
						data = r.results;
					}
				});
				return data;
			}
		},
		{
			"fieldname": "accumulated_values",
			"label": __("Accumulated Values"),
			"fieldtype": "Check"
		}
	);
});
