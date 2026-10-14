// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// Helpers of the Treasury reports and dashboard charts. They stay in the desk bundle because a report
// reads its filters as soon as its script runs, before anything loaded on demand would be ready.
// The form helpers are in treasury_form.js, added to just the Treasury forms.

frappe.provide("erpnext.treasury");

// rows flagged `bold` (totals and section headings) are shown in bold, with links shown as plain text
erpnext.treasury.report_formatter = function (value, row, column, data, default_formatter) {
	if (!data || !data.bold) {
		return default_formatter(value, row, column, data);
	}

	const formatted =
		column.fieldtype === "Link"
			? frappe.utils.escape_html(value || "")
			: default_formatter(value, row, column, data);
	return `<b>${formatted}</b>`;
};

erpnext.treasury.get_company_filter = function () {
	return {
		fieldname: "company",
		label: __("Company"),
		fieldtype: "Link",
		options: "Company",
		default: frappe.defaults.get_user_default("Company"),
		reqd: 1,
	};
};

erpnext.treasury.get_as_on_date_filter = function () {
	return {
		fieldname: "as_on_date",
		label: __("As On Date"),
		fieldtype: "Date",
		default: frappe.datetime.get_today(),
		reqd: 1,
	};
};

// reports default to this fiscal year so far, the period users check most
erpnext.treasury.get_period_filters = function () {
	return [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
	];
};

erpnext.treasury.get_investment_filters = function () {
	return [
		{
			fieldname: "investment_type",
			label: __("Investment Type"),
			fieldtype: "Link",
			options: "Investment Type",
		},
		{
			fieldname: "issuer",
			label: __("Issuer"),
			fieldtype: "Link",
			options: "Financial Institution",
		},
	];
};
