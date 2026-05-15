// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// Cached before fiscal year filters are cleared when switching to Date Range
let last_fiscal_year_range = { from: null, to: null };

function update_last_fiscal_year_range() {
	const from_fy = frappe.query_report.get_filter_value("from_fiscal_year");
	const to_fy = frappe.query_report.get_filter_value("to_fiscal_year");

	if (from_fy) {
		last_fiscal_year_range.from = from_fy;
	}
	if (to_fy) {
		last_fiscal_year_range.to = to_fy;
	}
}

function set_filter_visibility_for_period_mode() {
	const filter_based_on = frappe.query_report.get_filter_value("filter_based_on");
	frappe.query_report.toggle_filter_display("from_fiscal_year", filter_based_on === "Date Range");
	frappe.query_report.toggle_filter_display("to_fiscal_year", filter_based_on === "Date Range");
	frappe.query_report.toggle_filter_display("period_start_date", filter_based_on === "Fiscal Year");
	frappe.query_report.toggle_filter_display("period_end_date", filter_based_on === "Fiscal Year");
}

function set_filter_values_silently(values) {
	const report = frappe.query_report;
	report._no_refresh = true;
	Object.keys(values).forEach((fieldname) => {
		const filter = report.get_filter(fieldname);
		if (filter) {
			filter.set_value(values[fieldname]);
		}
	});
	report._no_refresh = false;
}

function debounce_report_refresh(report, delay = 50) {
	if (report._refresh_debounced) {
		return;
	}

	const original_refresh = report.refresh.bind(report);
	let refresh_timeout;

	report.refresh = function (have_filters_changed) {
		if (report._no_refresh) {
			return;
		}
		clearTimeout(refresh_timeout);
		refresh_timeout = setTimeout(() => {
			update_last_fiscal_year_range();
			original_refresh(have_filters_changed);
		}, delay);
	};
	report._refresh_debounced = true;
}

function populate_dates_from_fiscal_years(from_fy, to_fy) {
	const default_fy = erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), false, false);
	from_fy = from_fy || last_fiscal_year_range.from || default_fy;
	to_fy = to_fy || last_fiscal_year_range.to || default_fy;

	return frappe.db
		.get_value("Fiscal Year", from_fy, "year_start_date")
		.then((from_r) => {
			return frappe.db.get_value("Fiscal Year", to_fy, "year_end_date").then((to_r) => {
				const period_start_date = from_r?.message?.year_start_date;
				const period_end_date = to_r?.message?.year_end_date;
				const updates = {};

				if (!frappe.query_report.get_filter_value("period_start_date") && period_start_date) {
					updates.period_start_date = period_start_date;
				}
				if (!frappe.query_report.get_filter_value("period_end_date") && period_end_date) {
					updates.period_end_date = period_end_date;
				}

				if (Object.keys(updates).length) {
					set_filter_values_silently(updates);
				}
			});
		});
}

function get_filters() {
	let filters = [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "filter_based_on",
			label: __("Filter Based On"),
			fieldtype: "Select",
			options: ["Fiscal Year", "Date Range"],
			default: "Fiscal Year",
			reqd: 1,
			on_change: function () {
				const filter_based_on = frappe.query_report.get_filter_value("filter_based_on");
				set_filter_visibility_for_period_mode();

				if (filter_based_on === "Date Range") {
					populate_dates_from_fiscal_years().then(() => frappe.query_report.refresh());
				} else {
					frappe.query_report.refresh();
				}
			},
		},
		{
			fieldname: "period_start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
			mandatory_depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "period_end_date",
			label: __("End Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
			mandatory_depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "from_fiscal_year",
			label: __("Start Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
			mandatory_depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
		},
		{
			fieldname: "to_fiscal_year",
			label: __("End Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
			mandatory_depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
		},
		{
			fieldname: "periodicity",
			label: __("Periodicity"),
			fieldtype: "Select",
			options: [
				{ value: "Monthly", label: __("Monthly") },
				{ value: "Quarterly", label: __("Quarterly") },
				{ value: "Half-Yearly", label: __("Half-Yearly") },
				{ value: "Yearly", label: __("Yearly") },
			],
			default: "Monthly",
			reqd: 1,
		},
		{
			fieldname: "type",
			label: __("Invoice Type"),
			fieldtype: "Select",
			options: [
				{ value: "Revenue", label: __("Revenue") },
				{ value: "Expense", label: __("Expense") },
			],
			default: "Revenue",
			reqd: 1,
		},
		{
			fieldname: "with_upcoming_postings",
			label: __("Show with upcoming revenue/expense"),
			fieldtype: "Check",
			default: 1,
		},
	];

	let fy_filters = filters.filter((x) => {
		return ["from_fiscal_year", "to_fiscal_year"].includes(x.fieldname);
	});
	let fiscal_year = erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), false, false);
	if (fiscal_year) {
		fy_filters.forEach((x) => {
			x.default = fiscal_year;
		});
		last_fiscal_year_range.from = fiscal_year;
		last_fiscal_year_range.to = fiscal_year;
	}

	return filters;
}

frappe.query_reports["Deferred Revenue and Expense"] = {
	filters: get_filters(),
	formatter: function (value, row, column, data, default_formatter) {
		return default_formatter(value, row, column, data);
	},
	onload: function (report) {
		debounce_report_refresh(report);
		update_last_fiscal_year_range();
		set_filter_visibility_for_period_mode();

		const filters = report.get_values();
		const fiscal_year = erpnext.utils.get_fiscal_year(frappe.datetime.get_today());

		if (fiscal_year && (!filters.period_start_date || !filters.period_end_date)) {
			populate_dates_from_fiscal_years(
				filters.from_fiscal_year || last_fiscal_year_range.from,
				filters.to_fiscal_year || last_fiscal_year_range.to
			);
		}
	},
};
