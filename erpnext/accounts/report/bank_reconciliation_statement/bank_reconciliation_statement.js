// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Bank Reconciliation Statement"] = {
	filters: [
		{
			fieldname: "account",
			default: frappe.defaults.get_user_default("Company")
				? locals[":Company"][frappe.defaults.get_user_default("Company")]["default_bank_account"]
				: "",
			get_query: function () {
				var company = frappe.query_report.get_filter_value("company");
				return {
					query: "erpnext.controllers.queries.get_account_list",
					filters: [
						["Account", "account_type", "in", "Bank, Cash"],
						["Account", "is_group", "=", 0],
						["Account", "disabled", "=", 0],
						["Account", "company", "=", company],
					],
				};
			},
		},
	],
	formatter: function (value, row, column, data, default_formatter, filter) {
		if (column.fieldname == "payment_entry" && value == __("Cheques and Deposits incorrectly cleared")) {
			column.link_onclick =
				"frappe.query_reports['Bank Reconciliation Statement'].open_utility_report()";
		}
		return default_formatter(value, row, column, data);
	},
	open_utility_report: function () {
		frappe.route_options = {
			company: frappe.query_report.get_filter_value("company"),
			account: frappe.query_report.get_filter_value("account"),
			report_date: frappe.query_report.get_filter_value("report_date"),
		};
		frappe.open_in_new_tab = true;
		frappe.set_route("query-report", "Cheques and Deposits Incorrectly cleared");
	},
};
