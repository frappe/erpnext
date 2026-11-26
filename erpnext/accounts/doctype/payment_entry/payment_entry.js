// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.provide("erpnext.accounts.dimensions");

erpnext.accounts.taxes.setup_tax_validations("Payment Entry");
erpnext.accounts.taxes.setup_tax_filters("Advance Taxes and Charges");

frappe.ui.form.on("Payment Entry", {
	onload: function (frm) {
		frm.ignore_doctypes_on_cancel_all = [
			"Sales Invoice",
			"Purchase Invoice",
			"Journal Entry",
			"Repost Payment Ledger",
			"Repost Accounting Ledger",
			"Unreconcile Payment",
			"Unreconcile Payment Entries",
			"Bank Transaction",
		];

		if (frm.doc.__islocal) {
			if (!frm.doc.paid_from) frm.set_value("paid_from_account_currency", null);
			if (!frm.doc.paid_to) frm.set_value("paid_to_account_currency", null);
		}

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);

		// project excluded in setup_dimension_filters
		frm.set_query("project", function (doc) {
			let filters = {
				company: doc.company,
			};
			if (doc.party_type == "Customer") filters.customer = doc.party;
			return {
				query: "erpnext.controllers.queries.get_project_name",
				filters,
			};
		});

		if (frm.is_new()) {
			set_default_party_type(frm);
			frm.clear_table("tax_withholding_entries");
		}
	},

	setup: function (frm) {
		frm.cscript.tax_table = "Advance Taxes and Charges";
		frm.set_query("mode_of_payment", () => ({ filters: { enabled: 1 } }));
		frm.add_fetch("mode_of_payment", "type", "mode_of_payment_type");

		if (frappe.is_mobile()) {
			frm.get_field("references").grid.editable_fields = [
				{ fieldname: "reference_name", columns: 4 },
				{ fieldname: "outstanding_amount", columns: 3 },
				{ fieldname: "allocated_amount", columns: 3 },
			];
		}

		frm.set_query("paid_from", function (doc) {
			frm.events.validate_company(frm);

			var account_types = ["Pay", "Internal Transfer"].includes(frm.doc.payment_type)
				? ["Bank", "Cash"]
				: [frappe.boot.party_account_types[frm.doc.party_type]];
			let filters = {
				account_type: ["in", account_types],
				is_group: 0,
				company: doc.company,
			};

			if (frm.doc.party_type == "Shareholder") {
				account_types.push("Equity");
			}
			if (doc.payment_type == "Internal Transfer" && doc.paid_to) {
				filters.name = ["!=", doc.paid_to];
			}

			return {
				filters,
			};
		});

		frm.set_query("party_type", function () {
			return {
				filters: {
					name: ["in", Object.keys(frappe.boot.party_account_types)],
				},
			};
		});

		frm.set_query("party_bank_account", function () {
			return {
				filters: {
					is_company_account: 0,
					party_type: frm.doc.party_type,
					party: frm.doc.party,
				},
			};
		});

		frm.set_query("bank_account", function () {
			return {
				filters: {
					is_company_account: 1,
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("contact_person", function () {
			if (frm.doc.party) {
				return {
					query: "frappe.contacts.doctype.contact.contact.contact_query",
					filters: {
						link_doctype: frm.doc.party_type,
						link_name: frm.doc.party,
					},
				};
			}
		});

		frm.set_query("paid_to", function (doc) {
			frm.events.validate_company(frm);

			var account_types = ["Receive", "Internal Transfer"].includes(frm.doc.payment_type)
				? ["Bank", "Cash"]
				: [frappe.boot.party_account_types[frm.doc.party_type]];
			let filters = {
				account_type: ["in", account_types],
				is_group: 0,
				company: doc.company,
			};
			if (frm.doc.party_type == "Shareholder") {
				account_types.push("Equity");
			}
			if (doc.payment_type == "Internal Transfer" && doc.paid_from) {
				filters.name = ["!=", doc.paid_from];
			}
			return {
				filters,
			};
		});

		frm.set_query("account", "deductions", function () {
			return {
				filters: {
					is_group: 0,
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("advance_tax_account", function () {
			return {
				filters: {
					company: frm.doc.company,
					root_type: ["in", ["Asset", "Liability"]],
					is_group: 0,
				},
			};
		});

		frm.set_query("reference_doctype", "references", function () {
			let doctypes = ["Journal Entry"];
			if (frm.doc.party_type == "Customer") {
				doctypes = ["Sales Order", "Sales Invoice", "Journal Entry", "Dunning"];
			} else if (frm.doc.party_type == "Supplier") {
				doctypes = ["Purchase Order", "Purchase Invoice", "Journal Entry"];
			}

			return {
				filters: { name: ["in", doctypes] },
			};
		});

		frm.set_query("payment_term", "references", function (frm, cdt, cdn) {
			const child = locals[cdt][cdn];
			if (
				["Purchase Invoice", "Sales Invoice"].includes(child.reference_doctype) &&
				child.reference_name
			) {
				return {
					query: "erpnext.controllers.queries.get_payment_terms_for_references",
					filters: {
						reference: child.reference_name,
					},
				};
			}
		});

		frm.set_query("reference_name", "references", function (doc, cdt, cdn) {
			const child = locals[cdt][cdn];
			const filters = { docstatus: 1, company: doc.company };
			const party_type_doctypes = [
				"Sales Invoice",
				"Sales Order",
				"Purchase Invoice",
				"Purchase Order",
				"Dunning",
			];

			if (party_type_doctypes.includes(child.reference_doctype)) {
				filters[doc.party_type.toLowerCase()] = doc.party;
			}

			return {
				filters: filters,
			};
		});

		frm.set_query("payment_request", "references", function (doc, cdt, cdn) {
			const row = frappe.get_doc(cdt, cdn);
			return {
				query: "erpnext.accounts.doctype.payment_request.payment_request.get_open_payment_requests_query",
				filters: {
					reference_doctype: row.reference_doctype,
					reference_name: row.reference_name,
					company: doc.company,
					status: ["!=", "Paid"],
					outstanding_amount: [">", 0], // for compatibility with old data
					docstatus: 1,
				},
			};
		});

		frm.set_query("sales_taxes_and_charges_template", function () {
			return {
				filters: {
					company: frm.doc.company,
					disabled: false,
				},
			};
		});

		frm.set_query("purchase_taxes_and_charges_template", function () {
			return {
				filters: {
					company: frm.doc.company,
					disabled: false,
				},
			};
		});

		frm.add_fetch(
			"payment_request",
			"outstanding_amount",
			"payment_request_outstanding",
			"Payment Entry Reference"
		);
	},

	refresh: function (frm) {
		erpnext.hide_company(frm);
		frm.events.hide_unhide_fields(frm);
		frm.events.set_dynamic_labels(frm);
		frm.events.show_general_ledger(frm);
		frm.events.set_party_description(frm);
		frm.events.set_difference_description(frm);
		frm.events.setup_reference_buttons(frm);
		frm.events.show_allocate_button(frm);
		erpnext.accounts.ledger_preview.show_accounting_ledger_preview(frm);
		// internal transfers have no party, so nothing hits the payment ledger
		if (frm.doc.party) {
			erpnext.accounts.show_payment_ledger(frm);
			erpnext.accounts.ledger_preview.show_payment_ledger_preview(frm);
		}
		if (
			frm.doc.docstatus === 1 &&
			frm.doc.references &&
			frm.doc.references.find((elem) => {
				return elem.exchange_gain_loss != 0;
			})
		) {
			frm.add_custom_button(
				__("View Exchange Gain/Loss Journals"),
				function () {
					frappe.set_route("List", "Journal Entry", {
						voucher_type: "Exchange Gain Or Loss",
						reference_name: frm.doc.name,
					});
				},
				__("View")
			);
		}
		erpnext.accounts.unreconcile_payment.add_unreconcile_btn(frm);
		frappe.flags.allocate_payment_amount = true;
	},

	validate: async function (frm) {
		await frm.events.set_exchange_gain_loss_deduction(frm);
	},

	validate_company: (frm) => {
		if (!frm.doc.company) {
			frappe.throw({ message: __("Please select a Company first."), title: __("Mandatory") });
		}
	},

	company: function (frm) {
		frm.trigger("party");
		frm.events.hide_unhide_fields(frm);
		frm.events.set_dynamic_labels(frm);
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
		erpnext.utils.set_letter_head(frm);
	},

	contact_person: function (frm) {
		frm.set_value("contact_email", "");
		erpnext.utils.get_contact_details(frm);
	},

	hide_unhide_fields: function (frm) {
		var company_currency = frm.doc.company
			? frappe.get_doc(":Company", frm.doc.company)?.default_currency
			: "";

		frm.toggle_display(
			"source_exchange_rate",
			frm.doc.paid_amount && frm.doc.paid_from_account_currency != company_currency
		);

		frm.toggle_display(
			"target_exchange_rate",
			frm.doc.received_amount &&
				frm.doc.paid_to_account_currency != company_currency &&
				frm.doc.paid_from_account_currency != frm.doc.paid_to_account_currency
		);

		frm.toggle_display("base_paid_amount", frm.doc.paid_from_account_currency != company_currency);
		frm.toggle_display(
			"paid_from_account_currency",
			frm.doc.paid_from_account_currency != company_currency
		);
		frm.toggle_display("paid_to_account_currency", frm.doc.paid_to_account_currency != company_currency);

		if (frm.doc.payment_type == "Pay") {
			frm.toggle_display(
				"base_total_taxes_and_charges",
				frm.doc.total_taxes_and_charges && frm.doc.paid_to_account_currency != company_currency
			);
		} else {
			frm.toggle_display(
				"base_total_taxes_and_charges",
				frm.doc.total_taxes_and_charges && frm.doc.paid_from_account_currency != company_currency
			);
		}

		frm.toggle_display(
			"base_received_amount",
			frm.doc.paid_to_account_currency != company_currency &&
				frm.doc.paid_from_account_currency != frm.doc.paid_to_account_currency &&
				frm.doc.base_paid_amount != frm.doc.base_received_amount
		);

		frm.toggle_display(
			"received_amount",
			frm.doc.payment_type == "Internal Transfer" ||
				frm.doc.paid_from_account_currency != frm.doc.paid_to_account_currency
		);

		frm.toggle_display(
			["base_total_allocated_amount"],
			frm.doc.paid_amount &&
				frm.doc.received_amount &&
				frm.doc.base_total_allocated_amount &&
				((frm.doc.payment_type == "Receive" &&
					frm.doc.paid_from_account_currency != company_currency) ||
					(frm.doc.payment_type == "Pay" && frm.doc.paid_to_account_currency != company_currency))
		);

		var party_amount = frm.doc.payment_type == "Receive" ? frm.doc.paid_amount : frm.doc.received_amount;

		frm.toggle_display(
			"write_off_difference_amount",
			frm.doc.difference_amount && frm.doc.party && frm.doc.total_allocated_amount > party_amount
		);
	},

	set_dynamic_labels: function (frm) {
		var company_currency = frm.doc.company
			? frappe.get_doc(":Company", frm.doc.company)?.default_currency
			: "";

		frm.set_currency_labels(
			[
				"base_paid_amount",
				"base_received_amount",
				"base_total_allocated_amount",
				"difference_amount",
				"base_paid_amount_after_tax",
				"base_received_amount_after_tax",
				"base_total_taxes_and_charges",
			],
			company_currency
		);

		frm.set_currency_labels(["paid_amount", "paid_amount_after_tax"], frm.doc.paid_from_account_currency);
		frm.set_currency_labels(
			["received_amount", "received_amount_after_tax"],
			frm.doc.paid_to_account_currency
		);

		var party_account_currency =
			frm.doc.payment_type == "Receive"
				? frm.doc.paid_from_account_currency
				: frm.doc.paid_to_account_currency;

		frm.set_currency_labels(
			[
				"total_outstanding_amount",
				"total_allocated_amount",
				"unallocated_amount",
				"total_taxes_and_charges",
			],
			party_account_currency
		);

		var currency_field =
			frm.doc.payment_type == "Receive" ? "paid_from_account_currency" : "paid_to_account_currency";
		frm.set_df_property("total_outstanding_amount", "options", currency_field);
		frm.set_df_property("total_allocated_amount", "options", currency_field);
		frm.set_df_property("unallocated_amount", "options", currency_field);
		frm.set_df_property("total_taxes_and_charges", "options", currency_field);

		frm.events.set_exchange_rate_descriptions(frm);
		frm.events.set_account_descriptions(frm);
		frm.events.set_display_labels(frm);

		frm.refresh_fields();

		const party_currency =
			frm.doc.payment_type === "Receive" ? "paid_from_account_currency" : "paid_to_account_currency";

		var reference_grid = frm.fields_dict["references"].grid;
		["total_amount", "outstanding_amount", "allocated_amount"].forEach((fieldname) => {
			reference_grid.update_docfield_property(fieldname, "options", party_currency);
		});

		reference_grid.refresh();
	},

	show_allocate_button: function (frm) {
		if (
			frm.doc.docstatus !== 1 ||
			!(flt(frm.doc.unallocated_amount) > 0) ||
			!["Customer", "Supplier"].includes(frm.doc.party_type) ||
			!frappe.model.can_write("Payment Reconciliation")
		) {
			return;
		}

		frm.add_custom_button(
			__("Allocate to Invoices"),
			() => {
				frappe.route_options = {
					company: frm.doc.company,
					party_type: frm.doc.party_type,
					party: frm.doc.party,
					payment_name: frm.doc.name,
				};
				frappe.set_route("Form", "Payment Reconciliation");
			},
			__("Actions")
		);
	},

	setup_reference_buttons: function (frm) {
		frm.fields_dict.references.grid
			.add_custom_button(__("Get Outstanding"), () => frm.trigger("get_outstanding_invoices"), "top")
			.toggle(frm.doc.docstatus === 0);
	},

	get_party_amount: function (frm) {
		return frm.doc.payment_type == "Receive" ? frm.doc.paid_amount : frm.doc.received_amount;
	},

	is_amount_from_references: function (frm) {
		return frm.amount_from_references === frm.doc.name;
	},

	get_invoice_outstanding: function (frm) {
		const order_doctypes = frm.events.get_order_doctypes(frm);
		return (frm.doc.references || [])
			.filter((row) => !order_doctypes.includes(row.reference_doctype))
			.reduce((total, row) => total + flt(row.outstanding_amount), 0);
	},

	is_outstanding_in_payment_direction: function (frm) {
		const net_outstanding = frm.events.get_invoice_outstanding(frm);
		const settles_invoices =
			(frm.doc.payment_type == "Receive" && frm.doc.party_type == "Customer") ||
			(frm.doc.payment_type == "Pay" && ["Supplier", "Employee"].includes(frm.doc.party_type));
		return settles_invoices ? net_outstanding > 0 : net_outstanding < 0;
	},

	set_default_bank_cash_account: async function (frm) {
		const bank_field = { Receive: "paid_to", Pay: "paid_from" }[frm.doc.payment_type];
		const is_chosen = () => frm.doc[bank_field] || frm.doc.mode_of_payment || frm.doc.bank_account;
		if (!bank_field || frm.doc[bank_field] || frm.doc.mode_of_payment) return;
		if (frm.doc.bank_account) return frm.trigger("bank_account");

		const { company, payment_type } = frm.doc;
		for (const account_type of ["Bank", "Cash"]) {
			const { message } = await frappe.call({
				method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_default_bank_cash_account",
				args: { company, account_type, fetch_balance: 0 },
			});
			if (is_chosen() || frm.doc.company != company || frm.doc.payment_type != payment_type) return;
			if (message?.account) return frm.set_value(bank_field, message.account);
		}
	},

	sync_references_with_accounts: function (frm) {
		if (frm.doc.references?.length && frm.events.is_amount_from_references(frm)) {
			frm.events.set_total_allocated_amount(frm);
		}
	},

	set_exchange_rate_descriptions: function (frm) {
		const company_currency = frm.doc.company
			? frappe.get_doc(":Company", frm.doc.company)?.default_currency
			: "";
		const describe = (currency, rate) =>
			"1 " + currency + " = " + (flt(rate) ? flt(rate, 9) : "[?]") + " " + company_currency;

		frm.set_df_property(
			"source_exchange_rate",
			"description",
			describe(frm.doc.paid_from_account_currency, frm.doc.source_exchange_rate)
		);
		frm.set_df_property(
			"target_exchange_rate",
			"description",
			describe(frm.doc.paid_to_account_currency, frm.doc.target_exchange_rate)
		);
	},

	set_display_labels: function (frm) {
		frm.set_df_property("party", "label", frm.doc.party_type ? __(frm.doc.party_type) : __("Party"));
		frm.set_df_property("reference_no", "label", __("Reference Number"));
		frm.set_df_property("reference_date", "label", __("Reference Date"));
		[
			[
				"book_advance_payments_in_separate_party_account",
				__("Book advance payments in separate party account"),
			],
			["apply_tds", __("Consider for tax withholding")],
			["ignore_tax_withholding_threshold", __("Ignore tax withholding threshold")],
			["override_tax_withholding_entries", __("Edit tax withholding entries")],
			["custom_remarks", __("Custom remarks")],
		].forEach(([fieldname, label]) => frm.set_df_property(fieldname, "label", label));

		const currency = frm.doc.paid_from_account_currency;
		const single_currency = currency && currency === frm.doc.paid_to_account_currency;
		const same_currency_transfer = single_currency && frm.doc.payment_type === "Internal Transfer";
		if (frm.doc.payment_type === "Receive" && single_currency) {
			frm.fields_dict.paid_amount.set_label(__("Received Amount") + " (" + currency + ")");
		}
		if (same_currency_transfer) {
			frm.fields_dict.paid_amount.set_label(__("Paid Amount") + " (" + currency + ")");
		}
		frm.set_df_property(
			"received_amount",
			"description",
			same_currency_transfer
				? __(
						"Reduce this if the bank deducted a fee. The difference is added under Deductions or Loss on save."
				  )
				: ""
		);

		frm.events.set_bank_total_description(frm);
	},

	set_bank_total_description: function (frm) {
		const bank_side = {
			Receive: ["received_amount_after_tax", "received_amount", frm.doc.paid_to_account_currency],
			Pay: ["paid_amount_after_tax", "paid_amount", frm.doc.paid_from_account_currency],
		}[frm.doc.payment_type];
		if (!bank_side) return;

		const [fieldname, amount_field, currency] = bank_side;
		const taxes = frm.doc.taxes?.length
			? flt(flt(frm.doc[fieldname]) - flt(frm.doc[amount_field]), precision(fieldname))
			: 0;
		let description = "";
		if (taxes > 0) {
			description = __("Includes {0} of taxes and charges.", [format_currency(taxes, currency)]);
		} else if (taxes < 0) {
			description = __("After deducting {0} of taxes and charges.", [
				format_currency(-taxes, currency),
			]);
		}
		frm.set_df_property(fieldname, "description", description);
	},

	set_account_descriptions: function (frm) {
		const party_account = frm.doc.party_type
			? __("The {0}'s account.", [__(frm.doc.party_type)])
			: __("The party's account.");
		const [paid_from, paid_to] = {
			Receive: [party_account, __("Bank or cash account the money is received into.")],
			Pay: [__("Bank or cash account the money is paid from."), party_account],
			"Internal Transfer": [
				__("Account the money is transferred from."),
				__("Account the money is transferred to."),
			],
		}[frm.doc.payment_type] || ["", ""];

		frm.set_df_property("paid_from", "description", paid_from);
		frm.set_df_property("paid_to", "description", paid_to);
	},

	set_party_description: function (frm) {
		if (frm.doc.docstatus === 0 && frm.doc.party && !frm.doc.company) {
			frm.set_df_property(
				"party",
				"description",
				__("Select a Company to fetch this party's details.")
			);
			return;
		}

		const show =
			frm.doc.docstatus === 0 &&
			frm.doc.party &&
			frm.doc.company &&
			["Customer", "Supplier"].includes(frm.doc.party_type);

		if (!show) {
			frm.set_df_property("party", "description", "");
			return;
		}

		const key = frm.events.get_party_balance_key(frm);
		const cached = frm.party_balance;
		if (cached?.key === key) {
			frm.set_df_property("party", "description", frm.events.get_party_balance_text(frm, cached));
			return;
		}

		frappe.call({
			method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_party_balance",
			args: {
				company: frm.doc.company,
				party_type: frm.doc.party_type,
				party: frm.doc.party,
				date: frm.doc.posting_date,
			},
			callback: (r) => {
				if (key !== frm.events.get_party_balance_key(frm)) return;
				frm.party_balance = { key, ...r.message };
				frm.events.set_party_description(frm);
			},
		});
	},

	get_party_balance_key: function (frm) {
		return [frm.doc.name, frm.doc.company, frm.doc.posting_date, frm.doc.party_type, frm.doc.party].join(
			"\n"
		);
	},

	get_party_balance_text: function (frm, { balance, currency }) {
		if (balance == null) return "";

		const amount = format_currency(Math.abs(balance), currency);

		if (Math.abs(flt(balance)) < 0.005) {
			return __("Nothing outstanding");
		}
		if (frm.doc.party_type === "Customer") {
			return balance > 0 ? __("Owes {0}", [amount]) : __("Has paid {0} in advance", [amount]);
		}
		return balance < 0 ? __("You owe {0}", [amount]) : __("You have paid {0} in advance", [amount]);
	},

	show_general_ledger: function (frm) {
		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(
				__("Ledger"),
				function () {
					frappe.route_options = {
						voucher_no: frm.doc.name,
						from_date: frm.doc.posting_date,
						to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
						company: frm.doc.company,
						categorize_by: "",
						show_cancelled_entries: frm.doc.docstatus === 2,
					};
					frappe.set_route("query-report", "General Ledger");
				},
				__("View")
			);
		}
	},

	payment_type: async function (frm) {
		set_default_party_type(frm);
		frm.events.set_account_descriptions(frm);
		frm.events.set_display_labels(frm);

		if (frm.doc.payment_type == "Internal Transfer") {
			if (frm.doc.party || frm.doc.paid_from || frm.doc.paid_to || frm.doc.references?.length) {
				frappe.show_alert({
					message: __("Party, accounts and references were cleared for Internal Transfer"),
					indicator: "orange",
				});
			}
			$.each(
				[
					"party",
					"party_type",
					"paid_from",
					"paid_to",
					"references",
					"total_allocated_amount",
					"party_name",
				],
				function (i, field) {
					frm.set_value(field, null);
				}
			);
		} else {
			await frm.set_value({ paid_from: null, paid_to: null });
			if (frm.doc.party) {
				frm.trigger("party");
			}

			if (frm.doc.mode_of_payment) {
				frm.events.mode_of_payment(frm);
			}
		}
		frm.layout.refresh_section_collapse();
	},

	mode_of_payment: function (frm) {
		if (frm.doc.payment_type == "Internal Transfer") return;
		erpnext.accounts.pos.get_payment_mode_account(frm, frm.doc.mode_of_payment, function (account) {
			let payment_account_field = frm.doc.payment_type == "Receive" ? "paid_to" : "paid_from";
			frm.set_value(payment_account_field, account);
		});
	},

	party_type: function (frm) {
		let party_types = Object.keys(frappe.boot.party_account_types);
		if (frm.doc.party_type && !party_types.includes(frm.doc.party_type)) {
			frm.set_value("party_type", "");
			frappe.throw(__("Party can only be one of {0}", [party_types.join(", ")]));
		}
		frm.events.set_display_labels(frm);

		frm.set_query("party", function () {
			if (frm.doc.party_type == "Employee") {
				return {
					query: "erpnext.controllers.queries.employee_query",
				};
			} else if (["Customer", "Supplier"].includes(frm.doc.party_type)) {
				return erpnext.queries.party(frm.doc);
			} else if (frm.doc.party_type == "Shareholder") {
				return {
					filters: {
						company: frm.doc.company,
					},
				};
			}
		});

		if (frm.doc.party) {
			$.each(
				[
					"party",
					"paid_from",
					"paid_to",
					"paid_from_account_currency",
					"paid_to_account_currency",
					"references",
					"total_allocated_amount",
				],
				function (i, field) {
					frm.set_value(field, null);
				}
			);
		}
	},

	party: function (frm) {
		if (frm.doc.contact_email || frm.doc.contact_person) {
			frm.set_value("contact_email", "");
			frm.set_value("contact_person", "");
		}

		if (!frm.doc.party || !frm.doc.company) {
			frm.events.set_party_description(frm);
		}

		if (!frm.doc.party && frm.doc.party_name) {
			frm.set_value("party_name", "");
		}

		if (frm.doc.payment_type && frm.doc.party_type && frm.doc.party && frm.doc.company) {
			if (!frm.doc.posting_date) {
				frappe.msgprint(__("Please select Posting Date before selecting Party"));
				frm.set_value("party", "");
				return;
			}

			erpnext.utils.get_employee_contact_details(frm);

			frm.set_party_account_based_on_party = true;

			let company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

			return frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_party_details",
				args: {
					company: frm.doc.company,
					party_type: frm.doc.party_type,
					party: frm.doc.party,
					date: frm.doc.posting_date,
					cost_center: frm.doc.cost_center,
				},
				callback: function (r, rt) {
					if (r.message) {
						frappe.run_serially([
							() => {
								if (frm.doc.payment_type == "Receive") {
									frm.set_value("paid_from", r.message.party_account);
									frm.set_value(
										"paid_from_account_currency",
										r.message.party_account_currency
									);
								} else if (frm.doc.payment_type == "Pay") {
									frm.set_value("paid_to", r.message.party_account);
									frm.set_value(
										"paid_to_account_currency",
										r.message.party_account_currency
									);
								}
							},
							() => frm.set_value("party_name", r.message.party_name),
							() => frm.events.set_party_description(frm),
							() => {
								if (frm.doc.references?.length) {
									frappe.show_alert({
										message: __(
											"Invoice rows were cleared because the party or payment type changed"
										),
										indicator: "orange",
									});
								}
								frm.clear_table("references");
							},
							() => frm.clear_table("tax_withholding_entries"),
							() => frm.events.hide_unhide_fields(frm),
							() => frm.events.set_dynamic_labels(frm),
							() => {
								frm.set_party_account_based_on_party = false;
								if (r.message.party_bank_account) {
									frm.set_value("party_bank_account", r.message.party_bank_account);
								}
								if (r.message.bank_account) {
									// Auto-filled default bank account should not override Mode of Payment account
									frm.set_bank_account_based_on_party = true;
									return frm
										.set_value("bank_account", r.message.bank_account)
										.finally(() => {
											frm.set_bank_account_based_on_party = false;
										});
								}
							},
							() =>
								frm.events.set_current_exchange_rate(
									frm,
									"source_exchange_rate",
									frm.doc.paid_from_account_currency,
									company_currency
								),
							() =>
								frm.events.set_current_exchange_rate(
									frm,
									"target_exchange_rate",
									frm.doc.paid_to_account_currency,
									company_currency
								),
							() => frm.events.set_default_bank_cash_account(frm),
						]);
					}
				},
			});
		}
	},

	apply_tds: function (frm) {
		if (!frm.doc.apply_tds) {
			frm.set_value("tax_withholding_category", "");
		} else if (["Customer", "Supplier"].includes(frm.doc.party_type)) {
			frappe.db.get_value(frm.doc.party_type, frm.doc.party, "tax_withholding_category", (values) => {
				frm.set_value("tax_withholding_category", values.tax_withholding_category);
			});
		}
		frm.clear_table("tax_withholding_entries");
	},

	paid_from: function (frm) {
		if (frm.set_party_account_based_on_party) return;

		frm.events.set_company_bank_account(frm);

		frm.events.set_account_currency_and_balance(
			frm,
			frm.doc.paid_from,
			"paid_from_account_currency",
			function (frm) {
				if (frm.doc.payment_type == "Pay") {
					frm.events.paid_amount(frm);
				}
				frm.events.paid_from_account_currency(frm);
				frm.events.sync_references_with_accounts(frm);
			}
		);
	},

	paid_to: function (frm) {
		if (frm.set_party_account_based_on_party) return;

		frm.events.set_company_bank_account(frm);

		frm.events.set_account_currency_and_balance(
			frm,
			frm.doc.paid_to,
			"paid_to_account_currency",
			function (frm) {
				if (frm.doc.payment_type == "Receive") {
					if (frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency) {
						if (frm.doc.source_exchange_rate) {
							frm.set_value("target_exchange_rate", frm.doc.source_exchange_rate);
						}
						frm.set_value("received_amount", frm.doc.paid_amount);
					} else {
						frm.events.received_amount(frm);
					}
				}
				frm.events.paid_to_account_currency(frm);
				frm.events.sync_references_with_accounts(frm);
			}
		);
	},

	set_account_currency_and_balance: function (frm, account, currency_field, callback_function) {
		if (frm.doc.posting_date && account) {
			frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_account_details",
				args: {
					account: account,
					date: frm.doc.posting_date,
					cost_center: frm.doc.cost_center,
				},
				callback: function (r, rt) {
					if (r.message) {
						frappe.run_serially([
							() => {
								// bank side amount is re-derived from the party side amount below
								// when the bank account currency changes
								if (r.message["account_currency"] == frm.doc[currency_field]) return;

								if (
									frm.doc.payment_type == "Pay" &&
									currency_field == "paid_from_account_currency" &&
									frm.doc.received_amount
								) {
									frm.doc.paid_amount = 0;
								} else if (
									frm.doc.payment_type == "Receive" &&
									currency_field == "paid_to_account_currency" &&
									frm.doc.paid_amount
								) {
									frm.doc.received_amount = 0;
								}
							},
							() => frm.set_value(currency_field, r.message["account_currency"]),
							() => {
								if (
									frm.doc.payment_type == "Receive" &&
									currency_field == "paid_to_account_currency"
								) {
									frm.toggle_reqd(
										["reference_no", "reference_date"],
										r.message["account_type"] == "Bank" ? 1 : 0
									);
									if (!frm.doc.received_amount && frm.doc.paid_amount)
										frm.events.paid_amount(frm);
								} else if (
									frm.doc.payment_type == "Pay" &&
									currency_field == "paid_from_account_currency"
								) {
									frm.toggle_reqd(
										["reference_no", "reference_date"],
										r.message["account_type"] == "Bank" ? 1 : 0
									);

									if (!frm.doc.paid_amount && frm.doc.received_amount)
										frm.events.received_amount(frm);
								}
							},
							() => {
								if (callback_function) callback_function(frm);

								frm.events.hide_unhide_fields(frm);
								frm.events.set_dynamic_labels(frm);
							},
						]);
					}
				},
			});
		}
	},

	paid_from_account_currency: function (frm) {
		if (!frm.doc.paid_from_account_currency || !frm.doc.company) return;
		let company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

		frm.events.set_current_exchange_rate(
			frm,
			"source_exchange_rate",
			frm.doc.paid_from_account_currency,
			company_currency
		);
	},

	paid_to_account_currency: function (frm) {
		if (!frm.doc.paid_to_account_currency || !frm.doc.company) return;
		let company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

		frm.events.set_current_exchange_rate(
			frm,
			"target_exchange_rate",
			frm.doc.paid_to_account_currency,
			company_currency
		);
	},

	set_current_exchange_rate: function (frm, exchange_rate_field, from_currency, to_currency) {
		frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				transaction_date: frm.doc.posting_date,
				from_currency: from_currency,
				to_currency: to_currency,
			},
			callback: function (r, rt) {
				const ex_rate = flt(r.message, frm.get_field(exchange_rate_field).get_precision());
				frm.set_value(exchange_rate_field, ex_rate);
			},
		});
	},

	posting_date: function (frm) {
		frm.events.paid_from_account_currency(frm);
		frm.events.paid_to_account_currency(frm);
		frm.events.set_party_description(frm);
	},

	source_exchange_rate: function (frm) {
		frm.events.set_exchange_rate_descriptions(frm);
		frm.set_paid_amount_based_on_received_amount = true;
		let company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

		if (frm.doc.paid_amount && frm.doc.source_exchange_rate) {
			frm.set_value("base_paid_amount", flt(frm.doc.paid_amount) * flt(frm.doc.source_exchange_rate));
			frm.set_value("base_received_amount", frm.doc.base_paid_amount);

			// target exchange rate should always be same as source if both account currencies is same
			if (frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency) {
				frm.set_value("target_exchange_rate", frm.doc.source_exchange_rate);
				frm.set_value("received_amount", frm.doc.paid_amount);
			} else {
				const target_rate =
					flt(frm.doc.target_exchange_rate) ||
					(company_currency == frm.doc.paid_to_account_currency ? 1 : 0);
				if (target_rate) {
					frm.set_value("received_amount", flt(frm.doc.base_received_amount) / target_rate);
				}
			}

			// set_unallocated_amount is called by below method,
			// no need trigger separately
			frm.events.set_total_allocated_amount(frm);
		}
		frm.set_paid_amount_based_on_received_amount = false;

		// Make read only if Accounts Settings doesn't allow stale rates
		frm.set_df_property("source_exchange_rate", "read_only", erpnext.stale_rate_allowed() ? 0 : 1);
	},

	target_exchange_rate: function (frm) {
		frm.events.set_exchange_rate_descriptions(frm);
		let company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

		if (frm.doc.received_amount && frm.doc.target_exchange_rate) {
			frm.set_value(
				"base_received_amount",
				flt(frm.doc.received_amount) * flt(frm.doc.target_exchange_rate)
			);
			frm.set_value("base_paid_amount", frm.doc.base_received_amount);

			if (frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency) {
				frm.set_value("source_exchange_rate", frm.doc.target_exchange_rate);
				frm.set_value("paid_amount", frm.doc.received_amount);
			} else {
				const source_rate =
					flt(frm.doc.source_exchange_rate) ||
					(company_currency == frm.doc.paid_from_account_currency ? 1 : 0);
				if (source_rate) {
					frm.set_value("paid_amount", flt(frm.doc.base_paid_amount) / source_rate);
				}
			}

			// set_unallocated_amount is called by below method,
			// no need trigger separately
			frm.events.set_total_allocated_amount(frm);
		}

		// Make read only if Accounts Settings doesn't allow stale rates
		frm.set_df_property("target_exchange_rate", "read_only", erpnext.stale_rate_allowed() ? 0 : 1);
	},

	paid_amount: function (frm) {
		frm.set_value("base_paid_amount", flt(frm.doc.paid_amount) * flt(frm.doc.source_exchange_rate));
		let company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		if (!frm.doc.received_amount) {
			frm.set_value("base_received_amount", frm.doc.base_paid_amount);
			if (company_currency == frm.doc.paid_to_account_currency) {
				frm.set_value("received_amount", frm.doc.base_paid_amount);
			} else if (frm.doc.target_exchange_rate) {
				frm.set_value(
					"received_amount",
					flt(frm.doc.base_paid_amount) / flt(frm.doc.target_exchange_rate)
				);
			}
		}
		frm.trigger("reset_received_amount");
		frm.events.hide_unhide_fields(frm);
	},

	received_amount: function (frm) {
		let company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		frm.set_paid_amount_based_on_received_amount = true;

		frm.set_value(
			"base_received_amount",
			flt(frm.doc.received_amount) * flt(frm.doc.target_exchange_rate)
		);

		if (!frm.doc.paid_amount) {
			frm.set_value("base_paid_amount", frm.doc.base_received_amount);
			if (company_currency == frm.doc.paid_from_account_currency) {
				frm.set_value("paid_amount", frm.doc.base_received_amount);
			} else if (frm.doc.source_exchange_rate) {
				frm.set_value(
					"paid_amount",
					flt(frm.doc.base_received_amount) / flt(frm.doc.source_exchange_rate)
				);
			}
		}

		if (frm.doc.payment_type == "Pay") frm.events.allocate_changed_amount(frm, frm.doc.received_amount);
		else frm.events.set_unallocated_amount(frm);

		frm.set_paid_amount_based_on_received_amount = false;
		frm.events.hide_unhide_fields(frm);
	},

	reset_received_amount: function (frm) {
		if (
			!frm.set_paid_amount_based_on_received_amount &&
			frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency
		) {
			frm.set_value("received_amount", frm.doc.paid_amount);

			if (frm.doc.source_exchange_rate) {
				frm.set_value("target_exchange_rate", frm.doc.source_exchange_rate);
			}
			frm.set_value("base_received_amount", frm.doc.base_paid_amount);
		}

		if (frm.doc.payment_type == "Receive") frm.events.allocate_changed_amount(frm, frm.doc.paid_amount);
		else frm.events.set_unallocated_amount(frm);
	},

	allocate_changed_amount: function (frm, amount) {
		const total = Math.abs(
			(frm.doc.references || []).reduce((sum, row) => sum + flt(row.allocated_amount), 0)
		);
		if (!flt(amount) && total) {
			frm.amount_from_references = frm.doc.name;
			return frm.events.set_total_allocated_amount(frm);
		}

		if (frm.events.is_amount_from_references(frm)) {
			if (flt(amount, precision("paid_amount")) == flt(total, precision("paid_amount"))) {
				if (frm.doc.taxes?.length) frm.events.apply_taxes(frm);
				return frm.events.set_unallocated_amount(frm);
			}
			frm.amount_from_references = null;
		}
		return frm.events.allocate_party_amount_against_ref_docs(frm, amount, true);
	},

	set_amount_from_references: function (frm, total) {
		if (!frm.doc.paid_from_account_currency || !frm.doc.paid_to_account_currency) return;

		const amount = flt(total, precision("paid_amount"));
		const party_amount_field = frm.doc.payment_type == "Receive" ? "paid_amount" : "received_amount";
		if (flt(frm.doc[party_amount_field], precision(party_amount_field)) == amount) return;

		if (frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency) {
			return frm.set_value("paid_amount", amount);
		}
		return frm.doc.payment_type == "Receive"
			? frm.set_value({ received_amount: 0, paid_amount: amount })
			: frm.set_value({ paid_amount: 0, received_amount: amount });
	},

	get_outstanding_invoices_or_orders: function (frm, get_outstanding_invoices, get_orders_to_be_billed) {
		const amount = flt(frm.events.get_party_amount(frm));
		const ask_to_allocate = amount && !frm.events.is_amount_from_references(frm);
		const currency =
			frm.doc.payment_type == "Receive"
				? frm.doc.paid_from_account_currency
				: frm.doc.paid_to_account_currency;
		const formatted_amount = format_currency(amount, currency);
		const for_invoices = 'eval:doc.document_type != "Orders"';
		const date_fields = ["from_posting_date", "to_posting_date", "from_due_date", "to_due_date"];

		const left = [
			{
				fieldtype: "Date",
				label: __("From Due Date"),
				fieldname: "from_due_date",
				depends_on: for_invoices,
			},
			{ fieldtype: "Float", label: __("Outstanding Above"), fieldname: "outstanding_amt_greater_than" },
		];
		const right = [
			{
				fieldtype: "Date",
				label: __("To Due Date"),
				fieldname: "to_due_date",
				depends_on: for_invoices,
			},
			{ fieldtype: "Float", label: __("Outstanding Below"), fieldname: "outstanding_amt_less_than" },
		];
		(frm.dimension_filters || []).forEach((elem, idx) => {
			(idx % 2 ? right : left).push({
				fieldtype: "Link",
				label: elem.document_type == "Cost Center" ? __("Cost Center") : elem.label,
				options: elem.document_type,
				fieldname: elem.fieldname || elem.document_type,
			});
		});

		const fields = [
			{
				fieldtype: "Select",
				label: __("Document Type"),
				fieldname: "document_type",
				options: [
					{ label: __("Invoices"), value: "Invoices" },
					{ label: __("Orders"), value: "Orders" },
				],
				default: get_orders_to_be_billed ? "Orders" : "Invoices",
				hidden: !["Customer", "Supplier"].includes(frm.doc.party_type),
				change: () => dialog && update_labels(),
			},
			{ fieldtype: "Section Break", depends_on: for_invoices },
			{
				fieldtype: "Date",
				label: __("From Date"),
				fieldname: "from_posting_date",
				description: __("Leave both dates empty to include all open invoices."),
			},
			{ fieldtype: "Column Break" },
			{ fieldtype: "Date", label: __("To Date"), fieldname: "to_posting_date" },
			{ fieldtype: "Section Break", label: __("More Filters"), collapsible: 1 },
			...left,
			{ fieldtype: "Column Break" },
			...right,
		];

		if (ask_to_allocate) {
			fields.push(
				{ fieldtype: "Section Break" },
				{
					fieldtype: "Check",
					label: __("Allocate Payment Amount"),
					fieldname: "allocate_payment_amount",
					default: 1,
				}
			);
		}

		const dialog = new frappe.ui.Dialog({
			title: __("Get Outstanding"),
			fields: fields,
			primary_action_label: __("Get"),
			primary_action: (values) => {
				const get_orders = values.document_type == "Orders";
				const filters = { ...values };
				delete filters.document_type;
				if (get_orders) date_fields.forEach((field) => delete filters[field]);

				frm.events.validate_filters_data(frm, filters);
				frm.doc.cost_center = filters.cost_center;
				if (!ask_to_allocate) filters.allocate_payment_amount = 1;
				if (!get_orders) filters.limit = 500;

				dialog.hide();
				frm.events.get_outstanding_documents(frm, filters, !get_orders, get_orders);
			},
		});

		const update_labels = () => {
			const get_orders = dialog.get_value("document_type") == "Orders";
			dialog.get_primary_btn().text(get_orders ? __("Get Orders") : __("Get Invoices"));
			if (ask_to_allocate) {
				dialog.set_df_property(
					"allocate_payment_amount",
					"description",
					get_orders
						? __("Applies {0} to these orders, oldest first.", [formatted_amount])
						: __("Applies {0} to these invoices, oldest due first.", [formatted_amount])
				);
			}
		};

		dialog.show();
		update_labels();
	},

	get_outstanding_invoices: function (frm) {
		frm.events.get_outstanding_invoices_or_orders(frm, true, false);
	},

	get_outstanding_orders: function (frm) {
		frm.events.get_outstanding_invoices_or_orders(frm, false, true);
	},

	validate_filters_data: function (frm, filters) {
		const ranges = {
			[__("Posting Date")]: ["from_posting_date", "to_posting_date"],
			[__("Due Date")]: ["from_due_date", "to_due_date"],
		};

		for (let [label, [from_field, to_field]] of Object.entries(ranges)) {
			if (filters[from_field] && filters[to_field] && filters[from_field] > filters[to_field]) {
				frappe.throw(__("{0}: From Date must be on or before To Date", [label]));
			}
		}
	},

	get_outstanding_documents: function (frm, filters, get_outstanding_invoices, get_orders_to_be_billed) {
		if (!frm.doc.party) {
			return;
		}

		frm.events.check_mandatory_to_fetch(frm);
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

		var args = {
			posting_date: frm.doc.posting_date,
			company: frm.doc.company,
			party_type: frm.doc.party_type,
			payment_type: frm.doc.payment_type,
			party: frm.doc.party,
			party_account: frm.doc.payment_type == "Receive" ? frm.doc.paid_from : frm.doc.paid_to,
			cost_center: frm.doc.cost_center,
		};

		for (let key in filters) {
			args[key] = filters[key];
		}

		if (get_outstanding_invoices) {
			args["get_outstanding_invoices"] = true;
		} else if (get_orders_to_be_billed) {
			args["get_orders_to_be_billed"] = true;
		}

		if (frm.doc.book_advance_payments_in_separate_party_account) {
			args["book_advance_payments_in_separate_party_account"] = true;
		}

		frappe.flags.allocate_payment_amount = filters["allocate_payment_amount"];

		return frappe.call({
			method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding_reference_documents",
			args: {
				args: args,
			},
			callback: function (r, rt) {
				const key = (doctype, name, payment_term) => [doctype, name, payment_term || ""].join("\n");
				const existing = new Set(
					(frm.doc.references || []).map((row) =>
						key(row.reference_doctype, row.reference_name, row.payment_term)
					)
				);
				const new_rows = [];

				if (r.message) {
					$.each(r.message, function (i, d) {
						if (
							d.voucher_type == "Payment Entry" ||
							existing.has(key(d.voucher_type, d.voucher_no, d.payment_term))
						) {
							return;
						}

						var c = frm.add_child("references");
						new_rows.push(c);
						c.reference_doctype = d.voucher_type;
						c.reference_name = d.voucher_no;
						c.posting_date = d.posting_date;
						c.due_date = d.due_date;
						c.total_amount = d.invoice_amount;
						c.outstanding_amount = d.outstanding_amount;
						c.bill_no = d.bill_no;
						c.payment_term = d.payment_term;
						c.payment_term_outstanding = d.payment_term_outstanding;
						c.allocated_amount = d.allocated_amount;
						c.account = d.account;

						var party_account_currency =
							frm.doc.payment_type == "Receive"
								? frm.doc.paid_from_account_currency
								: frm.doc.paid_to_account_currency;

						if (party_account_currency != company_currency) {
							c.exchange_rate = d.exchange_rate;
						} else {
							c.exchange_rate = 1;
						}
						if (frm.events.get_invoice_doctypes(frm).includes(d.reference_doctype)) {
							c.due_date = d.due_date;
						}
					});
				}

				if (r.message?.length && !new_rows.length) {
					frappe.show_alert({
						message: get_outstanding_invoices
							? __("No new invoices to add.")
							: __("No new orders to add."),
						indicator: "blue",
					});
				}

				const open_invoices = new Set(
					(r.message || [])
						.filter((d) => flt(d.outstanding_amount) > 0)
						.map((d) => key(d.voucher_type, d.voucher_no))
				);
				if (filters.limit && open_invoices.size >= filters.limit) {
					frappe.show_alert(
						{
							message: __(
								"Showing the {0} oldest open invoices. Set a From Date to get newer ones.",
								[filters.limit]
							),
							indicator: "blue",
						},
						10
					);
				}

				if (
					(!flt(frm.events.get_party_amount(frm)) || frm.events.is_amount_from_references(frm)) &&
					frm.events.is_outstanding_in_payment_direction(frm)
				) {
					frm.amount_from_references = frm.doc.name;
					return frm.events.allocate_party_amount_against_ref_docs(
						frm,
						Math.abs(frm.events.get_invoice_outstanding(frm)),
						false
					);
				}
				frm.events.allocate_party_amount_against_ref_docs(
					frm,
					frm.events.get_party_amount(frm),
					false
				);
			},
		});
	},

	get_order_doctypes: function (frm) {
		return ["Sales Order", "Purchase Order"];
	},

	get_invoice_doctypes: function (frm) {
		return ["Sales Invoice", "Purchase Invoice"];
	},

	allocate_party_amount_against_ref_docs: async function (frm, paid_amount, paid_amount_change) {
		await frm.call("allocate_amount_to_references", {
			paid_amount: flt(paid_amount),
			paid_amount_change: paid_amount_change,
			allocate_payment_amount: frappe.flags.allocate_payment_amount ?? false,
		});

		if (frm.doc.taxes?.length) {
			frm.events.apply_taxes(frm);
		}
		frm.events.set_total_allocated_amount(frm);
	},

	set_total_allocated_amount: function (frm) {
		let exchange_rate = 1;
		if (frm.doc.payment_type == "Receive") {
			exchange_rate = frm.doc.source_exchange_rate;
		} else if (frm.doc.payment_type == "Pay") {
			exchange_rate = frm.doc.target_exchange_rate;
		}
		var total_allocated_amount = 0.0;
		var base_total_allocated_amount = 0.0;
		$.each(frm.doc.references || [], function (i, row) {
			if (row.allocated_amount) {
				total_allocated_amount += flt(row.allocated_amount);
				base_total_allocated_amount += flt(
					flt(row.allocated_amount) * flt(exchange_rate),
					precision("base_paid_amount")
				);
			}
		});
		const total_outstanding_amount = (frm.doc.references || []).reduce(
			(total, row) => total + flt(row.outstanding_amount),
			0
		);
		frm.set_value("total_outstanding_amount", flt(total_outstanding_amount, precision("paid_amount")));
		frm.set_value("total_allocated_amount", Math.abs(total_allocated_amount));
		frm.set_value("base_total_allocated_amount", Math.abs(base_total_allocated_amount));

		frm.events.set_unallocated_amount(frm);
		if (frm.events.is_amount_from_references(frm)) {
			return frm.events.set_amount_from_references(frm, Math.abs(total_allocated_amount));
		}
	},

	set_unallocated_amount: function (frm) {
		let unallocated_amount = 0;
		let deductions_to_consider = 0;

		for (const row of frm.doc.deductions || []) {
			if (!row.is_exchange_gain_loss) deductions_to_consider += flt(row.amount);
		}
		const included_taxes = get_included_taxes(frm);

		if (frm.doc.party) {
			if (
				frm.doc.payment_type == "Receive" &&
				frm.doc.base_total_allocated_amount < frm.doc.base_paid_amount + deductions_to_consider
			) {
				unallocated_amount =
					(frm.doc.base_paid_amount +
						deductions_to_consider -
						frm.doc.base_total_allocated_amount -
						included_taxes) /
					frm.doc.source_exchange_rate;
			} else if (
				frm.doc.payment_type == "Pay" &&
				frm.doc.base_total_allocated_amount < frm.doc.base_received_amount - deductions_to_consider
			) {
				unallocated_amount =
					(frm.doc.base_received_amount -
						deductions_to_consider -
						frm.doc.base_total_allocated_amount -
						included_taxes) /
					frm.doc.target_exchange_rate;
			}
		}
		frm.set_value("unallocated_amount", unallocated_amount);
		frm.trigger("set_difference_amount");
	},

	set_difference_amount: function (frm) {
		var difference_amount = 0;
		var base_unallocated_amount =
			flt(frm.doc.unallocated_amount) *
			(frm.doc.payment_type == "Receive" ? frm.doc.source_exchange_rate : frm.doc.target_exchange_rate);

		var base_party_amount = flt(frm.doc.base_total_allocated_amount) + base_unallocated_amount;
		const included_taxes = get_included_taxes(frm);

		if (frm.doc.payment_type == "Receive") {
			difference_amount = base_party_amount - flt(frm.doc.base_received_amount) + included_taxes;
		} else if (frm.doc.payment_type == "Pay") {
			difference_amount = flt(frm.doc.base_paid_amount) - base_party_amount - included_taxes;
		} else {
			difference_amount =
				flt(frm.doc.base_paid_amount) - flt(frm.doc.base_received_amount) - included_taxes;
		}

		var total_deductions = frappe.utils.sum(
			$.map(frm.doc.deductions || [], function (d) {
				return flt(d.amount);
			})
		);

		frm.set_value("difference_amount", difference_amount - total_deductions);

		frm.events.hide_unhide_fields(frm);
		frm.events.set_difference_description(frm);
		frm.layout.refresh_section_collapse();
	},

	set_difference_description: function (frm) {
		const doc = frm.doc;
		let description = "";

		const deductions = frappe.utils.sum((doc.deductions || []).map((row) => flt(row.amount)));
		const explain_deductions =
			doc.docstatus === 0 &&
			["Receive", "Pay"].includes(doc.payment_type) &&
			flt(doc.difference_amount) &&
			deductions &&
			!get_included_taxes(frm);

		if (explain_deductions) {
			const currency = frappe.get_doc(":Company", doc.company)?.default_currency;
			const format = (value) => format_currency(value, currency);
			const exchange_rate =
				doc.payment_type == "Receive" ? doc.source_exchange_rate : doc.target_exchange_rate;
			const settled =
				flt(doc.base_total_allocated_amount) + flt(doc.unallocated_amount) * flt(exchange_rate);

			description =
				doc.payment_type == "Receive"
					? __("{0} received + {1} deductions = {2}, but the invoices and advance add up to {3}.", [
							format(doc.base_received_amount),
							format(deductions),
							format(flt(doc.base_received_amount) + deductions),
							format(settled),
					  ])
					: __("{0} paid − {1} deductions = {2}, but the invoices and advance add up to {3}.", [
							format(doc.base_paid_amount),
							format(deductions),
							format(flt(doc.base_paid_amount) - deductions),
							format(settled),
					  ]);
		}

		const control = frm.fields_dict.difference_amount;
		if (description) {
			control.set_new_description(description);
		} else {
			control.set_empty_description();
		}
	},

	unallocated_amount: function (frm) {
		frm.trigger("set_difference_amount");
	},

	check_mandatory_to_fetch: function (frm) {
		$.each(["Company", "Party Type", "Party", "payment_type"], function (i, field) {
			if (!frm.doc[frappe.model.scrub(field)]) {
				frappe.msgprint(__("Please select {0} first", [field]));
				return false;
			}
		});
	},

	validate_reference_document: function (frm, row) {
		var _validate = function (i, row) {
			if (!row.reference_doctype) {
				return;
			}

			if (
				frm.doc.party_type == "Customer" &&
				!["Sales Order", "Sales Invoice", "Journal Entry", "Dunning"].includes(row.reference_doctype)
			) {
				frappe.model.set_value(row.doctype, row.name, "reference_doctype", null);
				frappe.msgprint(
					__(
						"Row #{0}: Reference Document Type must be one of Sales Order, Sales Invoice, Journal Entry or Dunning",
						[row.idx]
					)
				);
				return false;
			}

			if (
				frm.doc.party_type == "Supplier" &&
				!["Purchase Order", "Purchase Invoice", "Journal Entry"].includes(row.reference_doctype)
			) {
				frappe.model.set_value(row.doctype, row.name, "against_voucher_type", null);
				frappe.msgprint(
					__(
						"Row #{0}: Reference Document Type must be one of Purchase Order, Purchase Invoice or Journal Entry",
						[row.idx]
					)
				);
				return false;
			}
		};

		if (row) {
			_validate(0, row);
		} else {
			$.each(frm.doc.vouchers || [], _validate);
		}
	},

	write_off_difference_amount: function (frm) {
		frm.events.set_write_off_deduction(frm);
	},

	base_paid_amount: function (frm) {
		frm.events.set_exchange_gain_loss_deduction(frm);
		if (frm.doc.taxes?.length) {
			frm.events.apply_taxes(frm);
			frm.events.set_unallocated_amount(frm);
		}
	},

	base_received_amount: function (frm) {
		frm.events.set_exchange_gain_loss_deduction(frm);
	},

	set_exchange_gain_loss_deduction: async function (frm) {
		// wait for allocate_party_amount_against_ref_docs to finish
		await frappe.after_ajax();
		const base_paid_amount = frm.doc.base_paid_amount || 0;
		const base_received_amount = frm.doc.base_received_amount || 0;
		let other_deductions = 0;
		if (frm.doc.payment_type === "Internal Transfer") {
			other_deductions = (frm.doc.deductions || [])
				.filter((row) => !row.is_exchange_gain_loss)
				.reduce((sum, row) => sum + flt(row.amount), 0);
		}
		const exchange_gain_loss = flt(
			base_paid_amount - base_received_amount - other_deductions,
			get_deduction_amount_precision()
		);

		if (!exchange_gain_loss) {
			frm.events.delete_exchange_gain_loss(frm);
			return;
		}

		const account_fieldname = "exchange_gain_loss_account";
		let row = (frm.doc.deductions || []).find((t) => t.is_exchange_gain_loss);

		if (!row) {
			const company_defaults = frappe.get_doc(":Company", frm.doc.company);
			const is_single_currency =
				frm.doc.paid_from_account_currency === frm.doc.paid_to_account_currency;
			const account =
				(is_single_currency && company_defaults?.bank_charges_account) ||
				company_defaults?.[account_fieldname] ||
				(await prompt_for_missing_account(frm, account_fieldname));

			row = frm.add_child("deductions");
			row.account = account;
			row.cost_center = company_defaults?.cost_center;
			row.is_exchange_gain_loss = 1;
		}

		row.amount = exchange_gain_loss;
		frm.refresh_field("deductions");
		frm.events.set_unallocated_amount(frm);
	},

	delete_exchange_gain_loss: function (frm) {
		const exchange_gain_loss_row = (frm.doc.deductions || []).find((row) => row.is_exchange_gain_loss);

		if (!exchange_gain_loss_row) return;

		exchange_gain_loss_row.amount = 0;
		frm.get_field("deductions").grid.grid_rows[exchange_gain_loss_row.idx - 1].remove();
		frm.refresh_field("deductions");
	},

	set_write_off_deduction: async function (frm) {
		const difference_amount = flt(frm.doc.difference_amount, get_deduction_amount_precision());
		if (!difference_amount) return;

		const account_fieldname = "write_off_account";
		const response = await get_company_defaults(frm.doc.company);
		const write_off_account =
			response.message?.[account_fieldname] ||
			(await prompt_for_missing_account(frm, account_fieldname));

		if (!write_off_account) return;

		let row = (frm.doc["deductions"] || []).find((t) => t.account == write_off_account);
		if (!row) {
			row = frm.add_child("deductions");
			row.account = write_off_account;
			row.cost_center = response.message?.cost_center;
		}

		row.amount = flt(row.amount) + difference_amount;
		frm.refresh_field("deductions");
		frm.events.set_unallocated_amount(frm);

		frappe.show_alert({
			message: __("Wrote off {0} to {1}", [
				format_currency(
					Math.abs(difference_amount),
					frappe.get_doc(":Company", frm.doc.company).default_currency
				),
				write_off_account,
			]),
			indicator: "green",
		});
	},

	bank_account: function (frm) {
		if (frm.set_company_bank_account_based_on_coa) {
			frm.set_company_bank_account_based_on_coa = false;
			return;
		}

		// Only the current event is an automatic selection; later user edits must take precedence.
		const auto_filled = frm.set_bank_account_based_on_party;
		frm.set_bank_account_based_on_party = false;
		const { bank_account, company, payment_type, mode_of_payment } = frm.doc;
		const field = payment_type == "Pay" ? "paid_from" : "paid_to";
		if (bank_account && ["Pay", "Receive"].includes(payment_type)) {
			frappe.call({
				method: "erpnext.accounts.doctype.bank_account.bank_account.get_bank_account_details",
				args: {
					bank_account,
				},
				callback: function (r) {
					if (
						frm.doc.bank_account != bank_account ||
						frm.doc.company != company ||
						frm.doc.payment_type != payment_type ||
						frm.doc.mode_of_payment != mode_of_payment
					)
						return;

					if (r.message) {
						if (!auto_filled || !mode_of_payment) {
							frm.set_value(field, r.message.account);
						} else {
							frappe.call({
								method: "frappe.client.get_value",
								args: {
									doctype: "Mode of Payment Account",
									filters: {
										parent: mode_of_payment,
										company,
									},
									fieldname: "default_account",
									parent: "Mode of Payment",
								},
								callback: function (res) {
									if (
										frm.doc.bank_account != bank_account ||
										frm.doc.company != company ||
										frm.doc.payment_type != payment_type ||
										frm.doc.mode_of_payment != mode_of_payment
									)
										return;

									if (!res.message.default_account) {
										frm.set_value(field, r.message.account);
									}
								},
							});
						}
						frm.set_value("bank", r.message.bank);
						frm.set_value("bank_account_no", r.message.bank_account_no);
					}
				},
			});
		}
	},

	set_company_bank_account: function (frm) {
		if (!["Pay", "Receive"].includes(frm.doc.payment_type)) return;

		const field = frm.doc.payment_type == "Pay" ? "paid_from" : "paid_to";

		if (!frm.doc.company || !frm.doc[field]) return;

		const account = frm.doc[field];
		const { bank_account, company, payment_type } = frm.doc;

		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Bank Account",
				filters: {
					company,
					account,
					disabled: 0,
				},
				fieldname: ["name"],
			},
			callback: function (r) {
				if (
					frm.doc[field] != account ||
					frm.doc.bank_account != bank_account ||
					frm.doc.company != company ||
					frm.doc.payment_type != payment_type
				)
					return;

				if (r.message) {
					frm.set_company_bank_account_based_on_coa = true;
					return frm.set_value("bank_account", r.message.name).finally(() => {
						frm.set_company_bank_account_based_on_coa = false;
					});
				}
			},
		});
	},

	sales_taxes_and_charges_template: function (frm) {
		frm.trigger("fetch_taxes_from_template");
	},

	purchase_taxes_and_charges_template: function (frm) {
		frm.trigger("fetch_taxes_from_template");
	},

	fetch_taxes_from_template: function (frm) {
		let master_doctype = "";
		let taxes_and_charges = "";

		if (frm.doc.party_type == "Supplier") {
			master_doctype = "Purchase Taxes and Charges Template";
			taxes_and_charges = frm.doc.purchase_taxes_and_charges_template;
		} else if (frm.doc.party_type == "Customer") {
			master_doctype = "Sales Taxes and Charges Template";
			taxes_and_charges = frm.doc.sales_taxes_and_charges_template;
		}

		if (!taxes_and_charges) {
			return;
		}

		frappe.call({
			method: "erpnext.controllers.accounts_controller.get_taxes_and_charges",
			args: {
				master_doctype: master_doctype,
				master_name: taxes_and_charges,
			},
			callback: function (r) {
				if (!r.exc && r.message) {
					// set taxes table
					let taxes = r.message;
					taxes.forEach((tax) => {
						if (tax.charge_type === "On Net Total") {
							tax.charge_type = "On Paid Amount";
						}
					});
					frm.set_value("taxes", taxes);
					frm.events.apply_taxes(frm);
					frm.events.set_unallocated_amount(frm);
				}
			},
		});
	},

	apply_taxes: function (frm) {
		frm.events.initialize_taxes(frm);
		frm.events.determine_exclusive_rate(frm);
		frm.events.calculate_taxes(frm);
		frm.events.set_amounts_after_tax(frm);
	},

	set_amounts_after_tax: function (frm) {
		const base_applicable_tax = (frm.doc.taxes || [])
			.filter((tax) => !tax.included_in_paid_amount)
			.reduce(
				(total, tax) => total + (tax.add_deduct_tax == "Deduct" ? -1 : 1) * flt(tax.base_tax_amount),
				0
			);

		frm.doc.paid_amount_after_tax = flt(
			flt(frm.doc.paid_amount) + base_applicable_tax / flt(frm.doc.source_exchange_rate),
			precision("paid_amount_after_tax")
		);
		frm.doc.received_amount_after_tax = flt(
			flt(frm.doc.received_amount) + base_applicable_tax / flt(frm.doc.target_exchange_rate),
			precision("received_amount_after_tax")
		);
		frm.refresh_field("paid_amount_after_tax");
		frm.refresh_field("received_amount_after_tax");
		frm.events.set_bank_total_description(frm);
	},

	initialize_taxes: function (frm) {
		$.each(frm.doc["taxes"] || [], function (i, tax) {
			frm.events.validate_taxes_and_charges(tax);
			frm.events.validate_inclusive_tax(tax, frm);
			let tax_fields = [
				"total",
				"tax_fraction_for_current_item",
				"grand_total_fraction_for_current_item",
			];

			if (cstr(tax.charge_type) != "Actual") {
				tax_fields.push("tax_amount");
			}

			$.each(tax_fields, function (i, fieldname) {
				tax[fieldname] = 0.0;
			});

			frm.doc.paid_amount_after_tax = frm.doc.base_paid_amount;
		});
	},

	validate_taxes_and_charges: function (d) {
		let msg = "";

		if (d.account_head && !d.description) {
			// set description from account head
			d.description = d.account_head.split(" - ").slice(0, -1).join(" - ");
		}

		if (!d.charge_type && (d.row_id || d.rate || d.tax_amount)) {
			msg = __("Please select Charge Type first");
			d.row_id = "";
			d.rate = d.tax_amount = 0.0;
		} else if (
			(d.charge_type == "Actual" ||
				d.charge_type == "On Net Total" ||
				d.charge_type == "On Paid Amount") &&
			d.row_id
		) {
			msg = __(
				"Can refer row only if the charge type is 'On Previous Row Amount' or 'Previous Row Total'"
			);
			d.row_id = "";
		} else if (d.charge_type == "On Previous Row Amount" || d.charge_type == "On Previous Row Total") {
			if (d.idx == 1) {
				msg = __(
					"Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"
				);
				d.charge_type = "";
			} else if (!d.row_id) {
				d.row_id = d.idx - 1;
			} else if (d.row_id && d.row_id >= d.idx) {
				msg = __(
					"Cannot refer row number greater than or equal to current row number for this Charge type"
				);
				d.row_id = "";
			}
		}
		if (msg) {
			frappe.validated = false;
			refresh_field("taxes");
			frappe.throw(msg);
		}
	},

	validate_inclusive_tax: function (tax, frm) {
		let actual_type_error = function () {
			let msg = __("Actual type tax cannot be included in Item rate in row {0}", [tax.idx]);
			frappe.throw(msg);
		};

		let on_previous_row_error = function (row_range) {
			let msg = __("For row {0} in {1}. To include {2} in Item rate, rows {3} must also be included", [
				tax.idx,
				__(tax.doctype),
				tax.charge_type,
				row_range,
			]);
			frappe.throw(msg);
		};

		if (cint(tax.included_in_paid_amount)) {
			if (tax.charge_type == "Actual") {
				// inclusive tax cannot be of type Actual
				actual_type_error();
			} else if (
				tax.charge_type == "On Previous Row Amount" &&
				!cint(frm.doc["taxes"][tax.row_id - 1].included_in_paid_amount)
			) {
				// referred row should also be an inclusive tax
				on_previous_row_error(tax.row_id);
			} else if (tax.charge_type == "On Previous Row Total") {
				let taxes_not_included = $.map(frm.doc["taxes"].slice(0, tax.row_id), function (t) {
					return cint(t.included_in_paid_amount) ? null : t;
				});
				if (taxes_not_included.length > 0) {
					// all rows above this tax should be inclusive
					on_previous_row_error(tax.row_id == 1 ? "1" : "1 - " + tax.row_id);
				}
			}
		}
	},

	determine_exclusive_rate: function (frm) {
		let has_inclusive_tax = false;
		$.each(frm.doc["taxes"] || [], function (i, row) {
			if (cint(row.included_in_paid_amount)) has_inclusive_tax = true;
		});
		if (has_inclusive_tax == false) return;

		let cumulated_tax_fraction = 0.0;
		$.each(frm.doc["taxes"] || [], function (i, tax) {
			tax.tax_fraction_for_current_item = frm.events.get_current_tax_fraction(frm, tax);

			if (i == 0) {
				tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item;
			} else {
				tax.grand_total_fraction_for_current_item =
					frm.doc["taxes"][i - 1].grand_total_fraction_for_current_item +
					tax.tax_fraction_for_current_item;
			}

			cumulated_tax_fraction += tax.tax_fraction_for_current_item;
			frm.doc.paid_amount_after_tax = flt(frm.doc.base_paid_amount / (1 + cumulated_tax_fraction));
		});
	},

	get_current_tax_fraction: function (frm, tax) {
		let current_tax_fraction = 0.0;

		if (cint(tax.included_in_paid_amount)) {
			let tax_rate = tax.rate;

			if (tax.charge_type == "On Paid Amount") {
				current_tax_fraction = tax_rate / 100.0;
			} else if (tax.charge_type == "On Previous Row Amount") {
				current_tax_fraction =
					(tax_rate / 100.0) * frm.doc["taxes"][cint(tax.row_id) - 1].tax_fraction_for_current_item;
			} else if (tax.charge_type == "On Previous Row Total") {
				current_tax_fraction =
					(tax_rate / 100.0) *
					frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_fraction_for_current_item;
			}
		}

		if (tax.add_deduct_tax && tax.add_deduct_tax == "Deduct") {
			current_tax_fraction *= -1;
		}
		return current_tax_fraction;
	},

	calculate_taxes: function (frm) {
		frm.doc.total_taxes_and_charges = 0.0;
		frm.doc.base_total_taxes_and_charges = 0.0;

		let company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
		let actual_tax_dict = {};

		// maintain actual tax rate based on idx
		$.each(frm.doc["taxes"] || [], function (i, tax) {
			if (tax.charge_type == "Actual") {
				actual_tax_dict[tax.idx] = flt(tax.tax_amount, precision("tax_amount", tax));
			}
		});

		$.each(frm.doc["taxes"] || [], function (i, tax) {
			let current_tax_amount = frm.events.get_current_tax_amount(frm, tax);

			// Adjust divisional loss to the last item
			if (tax.charge_type == "Actual") {
				actual_tax_dict[tax.idx] -= current_tax_amount;
				if (i == frm.doc["taxes"].length - 1) {
					current_tax_amount += actual_tax_dict[tax.idx];
				}
			}

			// tax accounts are only in company currency
			tax.base_tax_amount = current_tax_amount;
			current_tax_amount *= tax.add_deduct_tax == "Deduct" ? -1.0 : 1.0;

			if (i == 0) {
				tax.total = flt(frm.doc.paid_amount_after_tax + current_tax_amount, precision("total", tax));
			} else {
				tax.total = flt(frm.doc["taxes"][i - 1].total + current_tax_amount, precision("total", tax));
			}

			// tac accounts are only in company currency
			tax.base_total = tax.total;

			// calculate total taxes and base total taxes
			if (frm.doc.payment_type == "Pay") {
				// tax accounts only have company currency
				if (tax.currency != frm.doc.paid_to_account_currency) {
					//total_taxes_and_charges has the target currency. so using target conversion rate
					frm.doc.total_taxes_and_charges += flt(current_tax_amount / frm.doc.target_exchange_rate);
				} else {
					frm.doc.total_taxes_and_charges += current_tax_amount;
				}
			} else if (frm.doc.payment_type == "Receive") {
				if (tax.currency != frm.doc.paid_from_account_currency) {
					//total_taxes_and_charges has the target currency. so using source conversion rate
					frm.doc.total_taxes_and_charges += flt(current_tax_amount / frm.doc.source_exchange_rate);
				} else {
					frm.doc.total_taxes_and_charges += current_tax_amount;
				}
			}

			frm.doc.base_total_taxes_and_charges += tax.base_tax_amount;

			frm.refresh_field("taxes");
			frm.refresh_field("total_taxes_and_charges");
			frm.refresh_field("base_total_taxes_and_charges");
		});
	},

	get_current_tax_amount: function (frm, tax) {
		let tax_rate = tax.rate;
		let current_tax_amount = 0.0;

		// To set row_id by default as previous row.
		if (["On Previous Row Amount", "On Previous Row Total"].includes(tax.charge_type)) {
			if (tax.idx === 1) {
				frappe.throw(
					__(
						"Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"
					)
				);
			}
		}

		if (tax.charge_type == "Actual") {
			current_tax_amount = flt(tax.tax_amount, precision("tax_amount", tax));
		} else if (tax.charge_type == "On Paid Amount") {
			current_tax_amount = flt((tax_rate / 100.0) * frm.doc.paid_amount_after_tax);
		} else if (tax.charge_type == "On Previous Row Amount") {
			current_tax_amount = flt((tax_rate / 100.0) * frm.doc["taxes"][cint(tax.row_id) - 1].tax_amount);
		} else if (tax.charge_type == "On Previous Row Total") {
			current_tax_amount = flt((tax_rate / 100.0) * frm.doc["taxes"][cint(tax.row_id) - 1].total);
		}

		return current_tax_amount;
	},

	before_save: function (frm) {
		frm.amount_follows_references_on_save = frm.events.is_amount_from_references(frm);
	},

	after_save: function (frm) {
		if (frm.amount_follows_references_on_save) {
			frm.amount_from_references = frm.doc.name;
		}

		const { matched_payment_requests } = frappe.last_response;
		if (!matched_payment_requests) return;

		const COLUMN_LABEL = [
			[__("Reference DocType"), __("Reference Name"), __("Allocated Amount"), __("Payment Request")],
		];

		frappe.msgprint({
			title: __("Unset Matched Payment Request"),
			message: COLUMN_LABEL.concat(matched_payment_requests),
			as_table: true,
			wide: true,
			primary_action: {
				label: __("Allocate Payment Request"),
				action() {
					frappe.hide_msgprint();
					frm.call("set_matched_payment_requests", { matched_payment_requests }, () => {
						frm.dirty();
					});
				},
			},
		});
	},

	before_cancel: function (frm) {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_linked_bank_transactions",
				args: { payment_entry: frm.doc.name },
				callback: function (r) {
					const linked = r.message || [];
					if (!linked.length) {
						resolve();
						return;
					}
					const bt_links = linked
						.map((name) => frappe.utils.get_form_link("Bank Transaction", name, true))
						.join(", ");
					frappe.confirm(
						__(
							"This Payment Entry is reconciled with {0}. Cancelling will automatically unreconcile it. Do you want to proceed?",
							[bt_links]
						),
						() => resolve(),
						() => reject(),
						__("Yes"),
						__("No")
					);
				},
			});
		});
	},
});

frappe.ui.form.on("Payment Entry Reference", {
	reference_doctype: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frm.events.validate_reference_document(frm, row);
	},

	reference_name: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.reference_name && row.reference_doctype) {
			return frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_reference_details",
				args: {
					reference_doctype: row.reference_doctype,
					reference_name: row.reference_name,
					party_account_currency:
						frm.doc.payment_type == "Receive"
							? frm.doc.paid_from_account_currency
							: frm.doc.paid_to_account_currency,
					party_type: frm.doc.party_type,
					party: frm.doc.party,
					party_account: frm.doc.payment_type == "Receive" ? frm.doc.paid_from : frm.doc.paid_to,
				},
				callback: function (r, rt) {
					if (r.message) {
						$.each(r.message, function (field, value) {
							frappe.model.set_value(cdt, cdn, field, value);
						});

						let allocated_amount =
							frm.doc.unallocated_amount > row.outstanding_amount
								? row.outstanding_amount
								: frm.doc.unallocated_amount;

						frappe.model.set_value(cdt, cdn, "allocated_amount", allocated_amount);
						frm.refresh_fields();
					}
				},
			});
		}
	},

	allocated_amount: function (frm) {
		frm.events.set_total_allocated_amount(frm);
	},

	references_remove: function (frm) {
		frm.events.set_total_allocated_amount(frm);
	},
});

frappe.ui.form.on("Advance Taxes and Charges", {
	rate: function (frm) {
		frm.events.apply_taxes(frm);
		frm.events.set_unallocated_amount(frm);
	},

	tax_amount: function (frm) {
		frm.events.apply_taxes(frm);
		frm.events.set_unallocated_amount(frm);
	},

	row_id: function (frm) {
		frm.events.apply_taxes(frm);
		frm.events.set_unallocated_amount(frm);
	},

	taxes_remove: function (frm) {
		frm.events.apply_taxes(frm);
		frm.events.set_unallocated_amount(frm);
	},

	included_in_paid_amount: function (frm) {
		frm.events.apply_taxes(frm);
		frm.events.set_unallocated_amount(frm);
	},

	charge_type: function (frm) {
		frm.events.apply_taxes(frm);
		frm.events.set_unallocated_amount(frm);
	},
});

frappe.ui.form.on("Payment Entry Deduction", {
	before_deductions_remove: function (doc, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.is_exchange_gain_loss && row.amount) {
			frappe.throw(__("Cannot delete a system-generated deduction row"));
		}
	},

	amount: function (frm) {
		if (frm.doc.payment_type === "Internal Transfer") {
			frm.events.set_exchange_gain_loss_deduction(frm);
		} else {
			frm.events.set_unallocated_amount(frm);
		}
	},

	deductions_remove: function (frm) {
		if (frm.doc.payment_type === "Internal Transfer") {
			frm.events.set_exchange_gain_loss_deduction(frm);
		} else {
			frm.events.set_unallocated_amount(frm);
		}
	},
});

function set_default_party_type(frm) {
	if (frm.doc.party) return;

	let party_type;
	if (frm.doc.payment_type == "Receive") {
		party_type = "Customer";
	} else if (frm.doc.payment_type == "Pay") {
		party_type = "Supplier";
	}

	if (party_type) frm.set_value("party_type", party_type);
}

function get_included_taxes(frm) {
	let included_taxes = 0;
	for (const tax of frm.doc.taxes) {
		if (!tax.included_in_paid_amount) continue;

		if (tax.add_deduct_tax == "Add") {
			included_taxes += tax.base_tax_amount;
		} else {
			included_taxes -= tax.base_tax_amount;
		}
	}

	return included_taxes;
}

function get_company_defaults(company) {
	return frappe.call({
		method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_company_defaults",
		args: {
			company: company,
		},
	});
}

function prompt_for_missing_account(frm, account) {
	return new Promise((resolve) => {
		const dialog = frappe.prompt(
			{
				label: __(frappe.unscrub(account)),
				fieldname: account,
				fieldtype: "Link",
				options: "Account",
				get_query: () => ({
					filters: {
						company: frm.doc.company,
					},
				}),
			},
			(values) => resolve(values?.[account]),
			__("Please Specify Account")
		);
	});
}

function get_deduction_amount_precision() {
	return frappe.meta.get_field_precision(frappe.meta.get_field("Payment Entry Deduction", "amount"));
}
