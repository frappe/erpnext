// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Invoice Discounting", {
	setup: (frm) => {
		frm.set_query("sales_invoice", "invoices", (doc) => {
			return {
				filters: {
					docstatus: 1,
					company: doc.company,
					outstanding_amount: [">", 0],
				},
			};
		});

		frm.events.filter_accounts("bank_account", frm, [["account_type", "=", "Bank"]]);
		frm.events.filter_accounts("bank_charges_account", frm, [["root_type", "=", "Expense"]]);
		frm.events.filter_accounts("short_term_loan", frm, [["root_type", "=", "Liability"]]);
		frm.events.filter_accounts("accounts_receivable_discounted", frm, [
			["account_type", "=", "Receivable"],
		]);
		frm.events.filter_accounts("accounts_receivable_credit", frm, [["account_type", "=", "Receivable"]]);
		frm.events.filter_accounts("accounts_receivable_unpaid", frm, [["account_type", "=", "Receivable"]]);
	},

	filter_accounts: (fieldname, frm, addl_filters) => {
		let filters = [
			["company", "=", frm.doc.company],
			["is_group", "=", 0],
		];
		if (addl_filters) {
			filters = $.merge(filters, addl_filters);
		}

		frm.set_query(fieldname, () => {
			return { filters: filters };
		});
	},

	refresh_filters: (frm) => {
		let invoice_accounts = Object.keys(frm.doc.invoices).map(function (key) {
			return frm.doc.invoices[key].debit_to;
		});
		let filters = [
			["account_type", "=", "Receivable"],
			["name", "not in", invoice_accounts],
		];
		frm.events.filter_accounts("accounts_receivable_credit", frm, filters);
		frm.events.filter_accounts("accounts_receivable_discounted", frm, filters);
		frm.events.filter_accounts("accounts_receivable_unpaid", frm, filters);
	},

	refresh: (frm) => {
		frm.events.show_general_ledger(frm);

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Get Invoices"), function () {
				frm.events.get_invoices(frm);
			});
		}

		if (frm.doc.docstatus === 1 && frm.doc.status !== "Settled") {
			if (frm.doc.status == "Sanctioned") {
				frm.add_custom_button(__("Disburse Loan"), function () {
					frm.events.create_disbursement_entry(frm);
				}).addClass("btn-primary");
			}
			if (frm.doc.status == "Disbursed") {
				frm.add_custom_button(__("Close Loan"), function () {
					frm.events.close_loan(frm);
				}).addClass("btn-primary");
			}
		}
	},

	loan_start_date: (frm) => {
		frm.events.set_end_date(frm);
	},

	loan_period: (frm) => {
		frm.events.set_end_date(frm);
	},

	set_end_date: (frm) => {
		if (frm.doc.loan_start_date && frm.doc.loan_period) {
			let end_date = frappe.datetime.add_days(frm.doc.loan_start_date, frm.doc.loan_period);
			frm.set_value("loan_end_date", end_date);
		}
	},

	validate: (frm) => {
		frm.events.calculate_total_amount(frm);
	},

	calculate_total_amount: (frm) => {
		let total_amount = 0.0;
		for (let row of frm.doc.invoices || []) {
			total_amount += flt(row.outstanding_amount);
		}
		frm.set_value("total_amount", total_amount);
	},
	get_invoices: (frm) => {
		var d = new frappe.ui.Dialog({
			title: __("Get Invoices based on Filters"),
			fields: [
				{
					label: "Customer",
					fieldname: "customer",
					fieldtype: "Link",
					options: "Customer",
				},
				{
					label: "From Date",
					fieldname: "from_date",
					fieldtype: "Date",
				},
				{
					label: "To Date",
					fieldname: "to_date",
					fieldtype: "Date",
				},
				{
					fieldname: "col_break",
					fieldtype: "Column Break",
				},
				{
					label: "Min Amount",
					fieldname: "min_amount",
					fieldtype: "Currency",
				},
				{
					label: "Max Amount",
					fieldname: "max_amount",
					fieldtype: "Currency",
				},
			],
			primary_action: function () {
				var data = d.get_values();

				frappe.call({
					method: "erpnext.accounts.doctype.invoice_discounting.invoice_discounting.get_invoices",
					args: {
						filters: data,
					},
					callback: function (r) {
						if (!r.exc) {
							d.hide();
							$.each(r.message, function (i, v) {
								frm.doc.invoices = frm.doc.invoices.filter((row) => row.sales_invoice);
								let row = frm.add_child("invoices");
								$.extend(row, v);
								frm.events.refresh_filters(frm);
							});
							refresh_field("invoices");
						}
					},
				});
			},
			primary_action_label: __("Get Invocies"),
		});
		d.show();
	},

	create_disbursement_entry: (frm) => {
		frappe.call({
			method: "create_disbursement_entry",
			doc: frm.doc,
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			},
		});
	},

	close_loan: (frm) => {
		frappe.call({
			method: "close_loan",
			doc: frm.doc,
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			},
		});
	},

	show_general_ledger: (frm) => {
		if (frm.doc.docstatus > 0) {
			cur_frm.add_custom_button(
				__("Accounting Ledger"),
				function () {
					frappe.route_options = {
						voucher_no: frm.doc.name,
						from_date: frm.doc.posting_date,
						to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
						company: frm.doc.company,
						group_by: "Group by Voucher (Consolidated)",
						show_cancelled_entries: frm.doc.docstatus === 2,
					};
					frappe.set_route("query-report", "General Ledger");
				},
				__("View")
			);
		}
	},
});

frappe.ui.form.on("Discounted Invoice", {
	sales_invoice: (frm) => {
		frm.events.calculate_total_amount(frm);
		frm.events.refresh_filters(frm);
	},
	invoices_remove: (frm) => {
		frm.events.calculate_total_amount(frm);
		frm.events.refresh_filters(frm);
	},
});
