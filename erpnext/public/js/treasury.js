// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.provide("erpnext.treasury");

// listed once so Investment and Investment Settings always offer the same accounts
erpnext.treasury.ACCOUNT_FIELDS = [
	"investment_account",
	"accrued_interest_account",
	"interest_income_account",
	"dividend_income_account",
	"realised_gain_loss_account",
	"unrealised_gain_loss_account",
	"fair_value_adjustment_account",
	"tax_withheld_receivable_account",
	"charges_account",
];

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

// General Ledger of this voucher, from `from_date` to the day it was last changed
erpnext.treasury.show_general_ledger = function (frm, from_date) {
	frappe.route_options = {
		voucher_no: frm.doc.name,
		from_date: from_date,
		to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
		company: frm.doc.company,
		categorize_by: "Categorize by Voucher (Consolidated)",
		show_cancelled_entries: frm.doc.docstatus === 2,
		ignore_prepared_report: true,
	};
	frappe.set_route("query-report", "General Ledger");
};

// an investment in company currency has nothing to convert, so its Exchange Rate is always 1
erpnext.treasury.set_conversion_rate = function (frm) {
	if (!frm.doc.currency || !frm.doc.company || frm.doc.docstatus !== 0) return;

	const is_company_currency = frm.doc.currency === erpnext.get_currency(frm.doc.company);
	frm.set_df_property("conversion_rate", "read_only", is_company_currency);

	if (is_company_currency && frm.doc.conversion_rate !== 1) {
		frm.set_value("conversion_rate", 1);
	}
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
