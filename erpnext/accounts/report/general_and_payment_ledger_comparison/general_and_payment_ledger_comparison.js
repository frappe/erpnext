// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

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
			fieldname: "period_start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "period_end_date",
			label: __("End Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "account",
			label: __("Account"),
			fieldtype: "MultiSelectList",
			options: "Account",
			get_data: function (txt) {
				return frappe.db.get_link_options("Account", txt, {
					company: frappe.query_report.get_filter_value("company"),
					account_type: ["in", ["Receivable", "Payable"]],
				});
			},
		},
		{
			fieldname: "voucher_no",
			label: __("Voucher No"),
			fieldtype: "Data",
			width: 100,
		},
	];
	return filters;
}

frappe.query_reports["General and Payment Ledger Comparison"] = {
	filters: get_filters(),

	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},

	onload: function (report) {
		report.page.add_inner_button(__("Repost Accounting Ledger"), function () {
			let indexes = frappe.query_report.datatable.rowmanager.getCheckedRows();
			let selected_rows = indexes.map((i) => frappe.query_report.data[i]);

			if (!selected_rows.length) frappe.throw(__("Please select at least one row."));

			let docs = selected_rows
				.filter((d) => d.docstatus === "Submitted")
				.map((d) => ({
					voucher_type: d.voucher_type,
					voucher_no: d.voucher_no,
				}));

			if (!docs.length) frappe.throw(__("No submitted documents selected."));

			frappe.confirm(
				__("Delete Cancelled Ledger Entries"),
				() => {
					frappe.call({
						method: "erpnext.accounts.report.general_and_payment_ledger_comparison.general_and_payment_ledger_comparison.repost_ledger",
						args: { docs, delete_existing: 1 },
						async: true,
						callback: function (r) {
							if (r.message) {
								console.log(r.message);
								let alert_message =
									`<a href='/app/repost-accounting-ledger/${r.message}' target='_blank'>` +
									__("Repost Initiated, click to view status") +
									`</a>`;
								frappe.show_alert({ message: alert_message, indicator: "orange" }, 10);
							} else {
								frappe.show_alert(
									{ message: __("Repost Initiated."), indicator: "orange" },
									10
								);
							}
							frappe.query_report.refresh();
						},
					});
				},
				() => {
					frappe.call({
						method: "erpnext.accounts.report.general_and_payment_ledger_comparison.general_and_payment_ledger_comparison.repost_ledger",
						args: { docs, delete_existing: 0 },
						async: true,
						callback: function (r) {
							if (r.message) {
								let data = r.message;
								let alert_message =
									`<a href='/app/repost-accounting-ledger/${data.name}' target='_blank'>` +
									__("Repost Initiated (without deleting existing), click to view status") +
									`</a>`;
								frappe.show_alert({ message: alert_message, indicator: "orange" }, 10);
							} else {
								frappe.show_alert(
									{
										message: __("Repost Initiated without deleting existing."),
										indicator: "orange",
									},
									10
								);
							}
							frappe.query_report.refresh();
						},
					});
				}
			);
		});
	},
};
