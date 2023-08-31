// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bank Reconciliation Tool Beta", {
	setup: function (frm) {
		frm.set_query("bank_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					"is_company_account": 1
				},
			};
		});

		frm.set_query("party_type", function () {
			return {
				filters: {
					name: [
						"in", Object.keys(frappe.boot.party_account_types),
					],
				},
			};
		});

	},

	onload: function (frm) {
		// Set default filter dates
		let today = frappe.datetime.get_today()
		frm.doc.bank_statement_from_date = frappe.datetime.add_months(today, -1);
		frm.doc.bank_statement_to_date = today;
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

	refresh: function(frm) {
		frm.disable_save();
		frm.fields_dict["filters_section"].collapse(false);

		frm.add_custom_button(__("Get Bank Transactions"), function() {
			if (!frm.doc.bank_account) {
				frappe.throw(
					{
						message: __("Please set the 'Bank Account' filter"),
						title: __("Filter Required")
					}
				);
			}

			frm.events.add_upload_statement_button(frm);
			frm.events.build_reconciliation_area(frm);
		});
		frm.change_custom_button_type("Get Bank Transactions", null, "primary");

		frm.add_custom_button(__("Auto Reconcile"), function() {
			frappe.call({
				method: "erpnext.accounts.doctype.bank_reconciliation_tool_beta.bank_reconciliation_tool_beta.auto_reconcile_vouchers",
				args: {
					bank_account: frm.doc.bank_account,
					from_date: frm.doc.bank_statement_from_date,
					to_date: frm.doc.bank_statement_to_date,
					filter_by_reference_date: frm.doc.filter_by_reference_date,
					from_reference_date: frm.doc.from_reference_date,
					to_reference_date: frm.doc.to_reference_date,
				},
				callback: function(r) {
					if (!r.exc) frm.refresh();
				}
			});
		});

		frm.$reconciliation_area = frm.get_field("reconciliation_action_area").$wrapper;
		frm.events.setup_empty_state(frm);

		frm.events.build_reconciliation_area(frm);
	},

	add_upload_statement_button: function(frm) {
		frm.remove_custom_button(__("Upload a Bank Statement"));
		frm.add_custom_button(
			__("Upload a Bank Statement"),
			() => frm.events.route_to_bank_statement_import(frm),
		);
	},

	setup_empty_state: function(frm) {
		frm.$reconciliation_area.empty();
		let empty_area = frm.$reconciliation_area.append(`
			<div class="bank-reco-beta-empty-state">
				<p>
					${__("Set Filters and Get Bank Transactions")}
				</p>
				<p>${__("Or")}</p>
			</div>
		`).find(".bank-reco-beta-empty-state");

		frappe.utils.add_custom_button(
			__("Upload a Bank Statement"),
			() => frm.events.route_to_bank_statement_import(frm),
			"",
			__("Upload a Bank Statement"),
			"btn-primary",
			$(empty_area),
		)
	},

	route_to_bank_statement_import(frm) {
		frappe.open_in_new_tab = true;

		if (!frm.doc.bank_account || !frm.doc.company) {
			frappe.new_doc("Bank Statement Import");
			return;
		}

		// Route to saved Import Record in new tab
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
					frappe.open_in_new_tab = true;
					frappe.set_route("Form", doc[0].doctype, doc[0].name);
				}
			},
		})
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
						frm.trigger("bank_statement_from_date");
						frm.trigger("bank_statement_to_date");
					}
				);
			}
		);

	},

	bank_statement_from_date: function (frm) {
		frm.trigger("get_account_opening_balance");
	},

	bank_statement_to_date: function (frm) {
		frm.trigger("get_account_closing_balance");
		frm.trigger("render_summary");
	},

	bank_statement_closing_balance: function (frm) {
		frm.trigger("render_summary");
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

	get_account_closing_balance(frm) {
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

	render_summary: function(frm) {
		frm.get_field("reconciliation_tool_cards").$wrapper.empty();

		frappe.require("bank-reconciliation-tool-beta.bundle.js", () => {
			let difference = flt(frm.doc.bank_statement_closing_balance) - flt(frm.cleared_balance);
			let difference_color = difference >= 0 ?  "text-success" : "text-danger";

			frm.summary_card = new erpnext.accounts.bank_reconciliation.SummaryCard({
				$wrapper: frm.get_field("reconciliation_tool_cards").$wrapper,
				values: {
					"Bank Closing Balance": [frm.doc.bank_statement_closing_balance],
					"ERP Closing Balance": [frm.cleared_balance],
					"Difference": [difference, difference_color]
				},
				currency: frm.doc.account_currency,
			})
		});
	},

	build_reconciliation_area: function(frm) {
		if (!frm.doc.bank_account) return;

		frappe.require("bank-reconciliation-tool-beta.bundle.js", () =>
			frm.panel_manager = new erpnext.accounts.bank_reconciliation.PanelManager({
				doc: frm.doc,
				$wrapper: frm.$reconciliation_area,
			})
		);
	},
});
