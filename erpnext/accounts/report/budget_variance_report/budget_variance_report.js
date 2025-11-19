// Copyright (c) 2015, Frappe Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Budget Variance Report"] = {
	filters: get_filters(),

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname && column.fieldname.includes("variance")) {
			if (data && data[column.fieldname] < 0) {
				value = "<span style='color:red'>" + value + "</span>";
			} else if (data && data[column.fieldname] > 0) {
				value = "<span style='color:green'>" + value + "</span>";
			}
		}

		return value;
	},
};

frappe.query_reports["Budget Variance Report"].onload = function (report) {
	let company = frappe.query_report.get_filter_value("company");
	if (!company) return;

	update_group_company_checkbox(company);
};

function update_group_company_checkbox(company) {
	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "Company",
			filters: { name: company },
			fieldname: "is_group",
		},
		callback: function (r) {
			const filter = frappe.query_report.get_filter("accumulated_in_group_company");
			if (!filter) return;

			if (r.message && r.message.is_group) {
				filter.df.hidden = 0;
			} else {
				filter.df.hidden = 1;
				frappe.query_report.set_filter_value("accumulated_in_group_company", 0);
			}
			filter.refresh();
		},
	});
}

function get_filters() {
	function get_dimensions() {
		let result = [];
		frappe.call({
			method: "erpnext.accounts.doctype.accounting_dimension.accounting_dimension.get_dimensions",
			args: {
				with_cost_center_and_project: true,
			},
			async: false,
			callback: function (r) {
				if (!r.exc) {
					result = r.message[0].map((elem) => elem.document_type);
				}
			},
		});
		return result;
	}

	let budget_against_options = get_dimensions();

	let filters = [
		{
			fieldname: "from_fiscal_year",
			label: __("From Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
			reqd: 1,
		},
		{
			fieldname: "to_fiscal_year",
			label: __("To Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
			reqd: 1,
		},
		{
			fieldname: "period",
			label: __("Period"),
			fieldtype: "Select",
			options: [
				{ value: "Monthly", label: __("Monthly") },
				{ value: "Quarterly", label: __("Quarterly") },
				{ value: "Half-Yearly", label: __("Half-Yearly") },
				{ value: "Yearly", label: __("Yearly") },
			],
			default: "Yearly",
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
			on_change: function () {
				let company = frappe.query_report.get_filter_value("company");
				if (company) update_group_company_checkbox(company);
			},
		},
		{
			fieldname: "budget_against",
			label: __("Budget Against"),
			fieldtype: "Select",
			options: budget_against_options,
			default: "Cost Center",
			reqd: 1,
			on_change: function () {
				frappe.query_report.set_filter_value("budget_against_filter", []);
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "budget_against_filter",
			label: __("Dimension Filter"),
			fieldtype: "MultiSelectList",
			options: "budget_against",
			get_data: function (txt) {
				let budget_against = frappe.query_report.get_filter_value("budget_against");
				if (!budget_against) return;

				return frappe.db.get_link_options(budget_against, txt);
			},
		},
		{
			fieldname: "show_cumulative",
			label: __("Show Cumulative Amount"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "accumulated_in_group_company",
			label: __("Accumulated Values in Group Company"),
			fieldtype: "Check",
			default: 0,
			hidden: 1,
		},
	];

	return filters;
}