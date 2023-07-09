// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.provide("erpnext.accounts.bank_reconciliation");

frappe.ui.form.on("Bank Reconciliation Tool", {
	setup: function (frm) {
		frm.set_query("bank_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					'is_company_account': 1
				},
			};
		});
		let no_bank_transactions_text =
			`<div class="text-muted text-center">${__("No Matching Bank Transactions Found")}</div>`
		set_field_options("no_bank_transactions", no_bank_transactions_text);
	},

	onload: function (frm) {
		// Set default filter dates
		let today = frappe.datetime.get_today()
		frm.doc.bank_statement_from_date = frappe.datetime.add_months(today, -1);
		frm.doc.bank_statement_to_date = today;
		frm.trigger('bank_account');
	},

	filter_by_reference_date: function (frm) {
		if (frm.doc.filter_by_reference_date) {
			frm.set_value("bank_statement_from_date", "");
			frm.set_value("bank_statement_to_date", "");
		} else {
			frm.set_value("from_reference_date", "");
			frm.set_value("to_reference_date", "");
		}
	},

	refresh: function (frm) {
		frm.disable_save();
		frappe.require("bank-reconciliation-tool.bundle.js", () =>
			frm.trigger("make_reconciliation_tool")
		);

		frm.add_custom_button(__("Upload Bank Statement"), () =>
				frappe.call({
					method:
						"erpnext.accounts.doctype.bank_statement_import.bank_statement_import.upload_bank_statement",
					args: {
						dt: frm.doc.doctype,
						dn: frm.doc.name,
						company: frm.doc.company,
						bank_account: frm.doc.bank_account,
					},
					callback: function (r) {
						if (!r.exc) {
							var doc = frappe.model.sync(r.message);
							frappe.set_route(
								"Form",
								doc[0].doctype,
								doc[0].name
							);
						}
					},
				})
		);

		frm.add_custom_button(__('Auto Reconcile'), function() {
			frappe.call({
				method: "erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.auto_reconcile_vouchers",
				args: {
					bank_account: frm.doc.bank_account,
					from_date: frm.doc.bank_statement_from_date,
					to_date: frm.doc.bank_statement_to_date,
					filter_by_reference_date: frm.doc.filter_by_reference_date,
					from_reference_date: frm.doc.from_reference_date,
					to_reference_date: frm.doc.to_reference_date,
				},
			})
		});

		frm.add_custom_button(__('Get Unreconciled Entries'), function() {
			frm.trigger("make_reconciliation_tool");
		});
		frm.change_custom_button_type('Get Unreconciled Entries', null, 'primary');

	},

	bank_account: function (frm) {
		frappe.db.get_value(
			"Bank Account",
			frm.doc.bank_account,
			"account",
			(r) => {
				frappe.db.get_value(
					"Account",
					r.account,
					"account_currency",
					(r) => {
						frm.doc.account_currency = r.account_currency;
						frm.trigger("render_chart");
					}
				);
			}
		);
		frm.trigger("get_account_opening_balance");
	},

	bank_statement_from_date: function (frm) {
		frm.trigger("get_account_opening_balance");
	},

	make_reconciliation_tool(frm) {
		frm.get_field("reconciliation_tool_cards").$wrapper.empty();
		if (frm.doc.bank_account && frm.doc.bank_statement_to_date) {
			frm.trigger("get_cleared_balance").then(() => {
				if (
					frm.doc.bank_account &&
					frm.doc.bank_statement_from_date &&
					frm.doc.bank_statement_to_date
				) {
					frm.trigger("render_chart");
					frm.trigger("render");
					frappe.utils.scroll_to(
						frm.get_field("reconciliation_tool_cards").$wrapper,
						true,
						30
					);
				}
			});
		}
	},

	get_account_opening_balance(frm) {
		if (frm.doc.bank_account && frm.doc.bank_statement_from_date) {
			frappe.call({
				method:
					"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_account_balance",
				args: {
					bank_account: frm.doc.bank_account,
					till_date: frm.doc.bank_statement_from_date,
				},
				callback: (response) => {
					frm.set_value("account_opening_balance", response.message);
				},
			});
		}
	},

	get_cleared_balance(frm) {
		if (frm.doc.bank_account && frm.doc.bank_statement_to_date) {
			return frappe.call({
				method:
					"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_account_balance",
				args: {
					bank_account: frm.doc.bank_account,
					till_date: frm.doc.bank_statement_to_date,
				},
				callback: (response) => {
					frm.cleared_balance = response.message;
				},
			});
		}
	},

	render_chart(frm) {
		frm.cards_manager = new erpnext.accounts.bank_reconciliation.NumberCardManager(
			{
				$reconciliation_tool_cards: frm.get_field(
					"reconciliation_tool_cards"
				).$wrapper,
				bank_statement_closing_balance:
				frm.doc.bank_statement_closing_balance,
				cleared_balance: frm.cleared_balance,
				currency: frm.doc.account_currency,
			}
		);
	},

	render(frm) {
		if (frm.doc.bank_account) {
			frm.bank_reconciliation_data_table_manager = new erpnext.accounts.bank_reconciliation.DataTableManager(
				{
					company: frm.doc.company,
					bank_account: frm.doc.bank_account,
					$reconciliation_tool_dt: frm.get_field(
						"reconciliation_tool_dt"
					).$wrapper,
					$no_bank_transactions: frm.get_field(
						"no_bank_transactions"
					).$wrapper,
					bank_statement_from_date: frm.doc.bank_statement_from_date,
					bank_statement_to_date: frm.doc.bank_statement_to_date,
					filter_by_reference_date: frm.doc.filter_by_reference_date,
					from_reference_date: frm.doc.from_reference_date,
					to_reference_date: frm.doc.to_reference_date,
					bank_statement_closing_balance:
						frm.doc.bank_statement_closing_balance,
					cards_manager: frm.cards_manager,
				}
			);
		}
	},
});
