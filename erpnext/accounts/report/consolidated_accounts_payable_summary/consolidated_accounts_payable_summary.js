// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Consolidated Accounts Payable Summary"] = {
	filters: [
		{
			fieldname: "companies",
			get_data: function (txt) {
				return erpnext.utils.get_link_options("Company", txt);
			},
			description: __("Totals are dropped when the companies use different currencies"),
		},
		{
			fieldname: "party_type",
			options: get_party_type_options(),
			on_change: function () {
				frappe.query_report.set_filter_value("party", "");
				frappe.query_report.toggle_filter_display(
					"supplier_group",
					frappe.query_report.get_filter_value("party_type") !== "Supplier"
				);
			},
		},
		{
			fieldname: "party",
			get_data: function (txt) {
				if (!frappe.query_report.filters) return;

				let party_type = frappe.query_report.get_filter_value("party_type");
				if (!party_type) return;

				return erpnext.utils.get_link_options(party_type, txt);
			},
		},
	],
	collapsible_filters: true,
	separate_check_filters: true,

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.bold) {
			value = value.bold();
		}
		return value;
	},

	onload: function (report) {
		report.page.add_inner_button(__("Consolidated Accounts Payable"), function () {
			frappe.set_route("query-report", "Consolidated Accounts Payable", report.get_values());
		});

		const company = frappe.defaults.get_user_default("Company");
		if (company && !(report.get_filter_value("companies") || []).length) {
			report.set_filter_value("companies", [company]);
		}

		if (frappe.boot.sysdefaults.default_ageing_range) {
			report.set_filter_value("range", frappe.boot.sysdefaults.default_ageing_range);
		}
	},
};

function get_party_type_options() {
	let options = [];
	frappe.db
		.get_list("Party Type", { filters: { account_type: "Payable" }, fields: ["name"] })
		.then((res) => {
			res.forEach((party_type) => {
				options.push(party_type.name);
			});
		});
	return options;
}
