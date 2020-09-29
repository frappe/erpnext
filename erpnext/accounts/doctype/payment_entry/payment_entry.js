// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
{% include "erpnext/public/js/controllers/accounts.js" %}

frappe.ui.form.on('Payment Entry', {
	onload: function(frm) {
		if(frm.doc.__islocal) {
			if (!frm.doc.paid_from) frm.set_value("paid_from_account_currency", null);
			if (!frm.doc.paid_to) frm.set_value("paid_to_account_currency", null);
		}
	},

	setup: function(frm) {
		frm.set_query("paid_from", function() {
			frm.events.validate_company(frm);

			var account_types = in_list(["Pay", "Internal Transfer"], frm.doc.payment_type) ?
				["Bank", "Cash"] : [frappe.boot.party_account_types[frm.doc.party_type]];
			return {
				filters: {
					"account_type": ["in", account_types],
					"is_group": 0,
					"company": frm.doc.company
				}
			}
		});

		frm.set_query("party_type", function() {
			frm.events.validate_company(frm);
			return{
				filters: {
					"name": ["in", Object.keys(frappe.boot.party_account_types)],
				}
			}
		});

		frm.set_query("party_bank_account", function() {
			return {
				filters: {
					is_company_account: 0,
					party_type: frm.doc.party_type,
					party: frm.doc.party
				}
			}
		});

		frm.set_query("bank_account", function() {
			return {
				filters: {
					is_company_account: 1
				}
			}
		});

		frm.set_query("contact_person", function() {
			if (frm.doc.party) {
				return {
					query: 'frappe.contacts.doctype.contact.contact.contact_query',
					filters: {
						link_doctype: frm.doc.party_type,
						link_name: frm.doc.party
					}
				};
			}
		});

		frm.set_query("paid_to", function() {
			frm.events.validate_company(frm);

			var account_types = in_list(["Receive", "Internal Transfer"], frm.doc.payment_type) ?
				["Bank", "Cash"] : [frappe.boot.party_account_types[frm.doc.party_type]];
			return {
				filters: {
					"account_type": ["in", account_types],
					"is_group": 0,
					"company": frm.doc.company
				}
			}
		});

		frm.set_query("account", "deductions", function() {
			return {
				filters: {
					"is_group": 0,
					"company": frm.doc.company
				}
			}
		});

		frm.set_query("cost_center", "deductions", function() {
			return {
				filters: {
					"is_group": 0,
					"company": frm.doc.company
				}
			}
		});

		frm.set_query("reference_doctype", "references", function() {
			if (frm.doc.party_type=="Customer") {
				var doctypes = ["Sales Order", "Sales Invoice", "Journal Entry"];
			} else if (frm.doc.party_type=="Supplier") {
				var doctypes = ["Purchase Order", "Purchase Invoice", "Journal Entry"];
			} else if (frm.doc.party_type=="Employee") {
				var doctypes = ["Expense Claim", "Journal Entry"];
			} else if (frm.doc.party_type=="Student") {
				var doctypes = ["Fees"];
			} else {
				var doctypes = ["Journal Entry"];
			}

			return {
				filters: { "name": ["in", doctypes] }
			};
		});

		frm.set_query('payment_term', 'references', function(frm, cdt, cdn) {
			const child = locals[cdt][cdn];
			if (in_list(['Purchase Invoice', 'Sales Invoice'], child.reference_doctype) && child.reference_name) {
				let payment_term_list = frappe.get_list('Payment Schedule', {'parent': child.reference_name});

				payment_term_list = payment_term_list.map(pt => pt.payment_term);

				return {
					filters: {
						'name': ['in', payment_term_list]
					}
				}
			}
		});

		frm.set_query("reference_name", "references", function(doc, cdt, cdn) {
			const child = locals[cdt][cdn];
			const filters = {"docstatus": 1, "company": doc.company};
			const party_type_doctypes = ['Sales Invoice', 'Sales Order', 'Purchase Invoice',
				'Purchase Order', 'Expense Claim', 'Fees'];

			if (in_list(party_type_doctypes, child.reference_doctype)) {
				filters[doc.party_type.toLowerCase()] = doc.party;
			}

			if(child.reference_doctype == "Expense Claim") {
				filters["docstatus"] = 1;
				filters["is_paid"] = 0;
			}

			return {
				filters: filters
			};
		});
	},

	refresh: function(frm) {
		erpnext.hide_company();
		frm.events.hide_unhide_fields(frm);
		frm.events.set_dynamic_labels(frm);
		frm.events.show_general_ledger(frm);
	},

	validate_company: (frm) => {
		if (!frm.doc.company){
			frappe.throw({message:__("Please select a Company first."), title: __("Mandatory")});
		}
	},

	company: function(frm) {
		frm.events.hide_unhide_fields(frm);
		frm.events.set_dynamic_labels(frm);
	},

	contact_person: function(frm) {
		frm.set_value("contact_email", "");
		erpnext.utils.get_contact_details(frm);
	},

	hide_unhide_fields: function(frm) {
		var company_currency = frm.doc.company? frappe.get_doc(":Company", frm.doc.company).default_currency: "";

		frm.toggle_display("source_exchange_rate",
			(frm.doc.paid_amount && frm.doc.paid_from_account_currency != company_currency));

		frm.toggle_display("target_exchange_rate", (frm.doc.received_amount &&
			frm.doc.paid_to_account_currency != company_currency &&
			frm.doc.paid_from_account_currency != frm.doc.paid_to_account_currency));

		frm.toggle_display("base_paid_amount", frm.doc.paid_from_account_currency != company_currency);

		frm.toggle_display("base_received_amount", (
			frm.doc.paid_to_account_currency != company_currency &&
			frm.doc.paid_from_account_currency != frm.doc.paid_to_account_currency 
			&& frm.doc.base_paid_amount != frm.doc.base_received_amount
		));

		frm.toggle_display("received_amount", (frm.doc.payment_type=="Internal Transfer" ||
			frm.doc.paid_from_account_currency != frm.doc.paid_to_account_currency))

		frm.toggle_display(["base_total_allocated_amount"],
			(frm.doc.paid_amount && frm.doc.received_amount && frm.doc.base_total_allocated_amount &&
			((frm.doc.payment_type=="Receive" && frm.doc.paid_from_account_currency != company_currency) ||
			(frm.doc.payment_type=="Pay" && frm.doc.paid_to_account_currency != company_currency))));

		var party_amount = frm.doc.payment_type=="Receive" ?
			frm.doc.paid_amount : frm.doc.received_amount;

		frm.toggle_display("write_off_difference_amount", (frm.doc.difference_amount && frm.doc.party &&
			(frm.doc.total_allocated_amount > party_amount)));

		frm.toggle_display("set_exchange_gain_loss",
			(frm.doc.paid_amount && frm.doc.received_amount && frm.doc.difference_amount &&
				((frm.doc.paid_from_account_currency != company_currency ||
					frm.doc.paid_to_account_currency != company_currency) &&
					frm.doc.paid_from_account_currency != frm.doc.paid_to_account_currency)));

		frm.refresh_fields();
	},

	set_dynamic_labels: function(frm) {
		var company_currency = frm.doc.company? frappe.get_doc(":Company", frm.doc.company).default_currency: "";

		frm.set_currency_labels(["base_paid_amount", "base_received_amount", "base_total_allocated_amount",
			"difference_amount"], company_currency);

		frm.set_currency_labels(["paid_amount"], frm.doc.paid_from_account_currency);
		frm.set_currency_labels(["received_amount"], frm.doc.paid_to_account_currency);

		var party_account_currency = frm.doc.payment_type=="Receive" ?
			frm.doc.paid_from_account_currency : frm.doc.paid_to_account_currency;

		frm.set_currency_labels(["total_allocated_amount", "unallocated_amount"], party_account_currency);

		var currency_field = (frm.doc.payment_type=="Receive") ? "paid_from_account_currency" : "paid_to_account_currency"
		frm.set_df_property("total_allocated_amount", "options", currency_field);
		frm.set_df_property("unallocated_amount", "options", currency_field);
		frm.set_df_property("party_balance", "options", currency_field);

		frm.set_currency_labels(["total_amount", "outstanding_amount", "allocated_amount"],
			party_account_currency, "references");

		frm.set_currency_labels(["amount"], company_currency, "deductions");

		cur_frm.set_df_property("source_exchange_rate", "description",
			("1 " + frm.doc.paid_from_account_currency + " = [?] " + company_currency));

		cur_frm.set_df_property("target_exchange_rate", "description",
			("1 " + frm.doc.paid_to_account_currency + " = [?] " + company_currency));

		frm.refresh_fields();
	},

	show_general_ledger: function(frm) {
		if(frm.doc.docstatus==1) {
			frm.add_custom_button(__('Ledger'), function() {
				frappe.route_options = {
					"voucher_no": frm.doc.name,
					"from_date": frm.doc.posting_date,
					"to_date": frm.doc.posting_date,
					"company": frm.doc.company,
					group_by: ""
				};
				frappe.set_route("query-report", "General Ledger");
			}, "fa fa-table");
		}
	},

	payment_type: function(frm) {
		if(frm.doc.payment_type == "Internal Transfer") {
			$.each(["party", "party_balance", "paid_from", "paid_to",
				"references", "total_allocated_amount"], function(i, field) {
				frm.set_value(field, null);
			});
		} else {
			if(frm.doc.party) {
				frm.events.party(frm);
			}

			if(frm.doc.mode_of_payment) {
				frm.events.mode_of_payment(frm);
			}
		}
	},

	party_type: function(frm) {

		let party_types = Object.keys(frappe.boot.party_account_types);
		if(frm.doc.party_type && !party_types.includes(frm.doc.party_type)){
			frm.set_value("party_type", "");
			frappe.throw(__("Party can only be one of "+ party_types.join(", ")));
		}

		if(frm.doc.party) {
			$.each(["party", "party_balance", "paid_from", "paid_to",
				"paid_from_account_currency", "paid_from_account_balance",
				"paid_to_account_currency", "paid_to_account_balance",
				"references", "total_allocated_amount"],
				function(i, field) {
					frm.set_value(field, null);
				})
		}
	},

	party: function(frm) {
		if (frm.doc.contact_email || frm.doc.contact_person) {
			frm.set_value("contact_email", "");
			frm.set_value("contact_person", "");
		}
		if(frm.doc.payment_type && frm.doc.party_type && frm.doc.party && frm.doc.company) {
			if(!frm.doc.posting_date) {
				frappe.msgprint(__("Please select Posting Date before selecting Party"))
				frm.set_value("party", "");
				return ;
			}
			frm.set_party_account_based_on_party = true;

			return frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_party_details",
				args: {
					company: frm.doc.company,
					party_type: frm.doc.party_type,
					party: frm.doc.party,
					date: frm.doc.posting_date,
					cost_center: frm.doc.cost_center
				},
				callback: function(r, rt) {
					if(r.message) {
						frappe.run_serially([
							() => {
								if(frm.doc.payment_type == "Receive") {
									frm.set_value("paid_from", r.message.party_account);
									frm.set_value("paid_from_account_currency", r.message.party_account_currency);
									frm.set_value("paid_from_account_balance", r.message.account_balance);
								} else if (frm.doc.payment_type == "Pay"){
									frm.set_value("paid_to", r.message.party_account);
									frm.set_value("paid_to_account_currency", r.message.party_account_currency);
									frm.set_value("paid_to_account_balance", r.message.account_balance);
								}
							},
							() => frm.set_value("party_balance", r.message.party_balance),
							() => frm.set_value("party_name", r.message.party_name),
							() => frm.clear_table("references"),
							() => frm.events.hide_unhide_fields(frm),
							() => frm.events.set_dynamic_labels(frm),
							() => {
								frm.set_party_account_based_on_party = false;
								if (r.message.bank_account) {
									frm.set_value("bank_account", r.message.bank_account);
								}
							}
						]);
					}
				}
			});
		}
	},

	paid_from: function(frm) {
		if(frm.set_party_account_based_on_party) return;

		frm.events.set_account_currency_and_balance(frm, frm.doc.paid_from,
			"paid_from_account_currency", "paid_from_account_balance", function(frm) {
				if (frm.doc.payment_type == "Pay") {
					frm.events.paid_amount(frm);
				}
			}
		);
	},

	paid_to: function(frm) {
		if(frm.set_party_account_based_on_party) return;

		frm.events.set_account_currency_and_balance(frm, frm.doc.paid_to,
			"paid_to_account_currency", "paid_to_account_balance", function(frm) {
				if (frm.doc.payment_type == "Receive") {
					if(frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency) {
						if(frm.doc.source_exchange_rate) {
							frm.set_value("target_exchange_rate", frm.doc.source_exchange_rate);
						}
						frm.set_value("received_amount", frm.doc.paid_amount);

					} else {
						frm.events.received_amount(frm);
					}
				}
			}
		);
	},

	set_account_currency_and_balance: function(frm, account, currency_field,
			balance_field, callback_function) {
		if (frm.doc.posting_date && account) {
			frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_account_details",
				args: {
					"account": account,
					"date": frm.doc.posting_date,
					"cost_center": frm.doc.cost_center
				},
				callback: function(r, rt) {
					if(r.message) {
						frappe.run_serially([
							() => frm.set_value(currency_field, r.message['account_currency']),
							() => {
								frm.set_value(balance_field, r.message['account_balance']);

								if(frm.doc.payment_type=="Receive" && currency_field=="paid_to_account_currency") {
									frm.toggle_reqd(["reference_no", "reference_date"],
										(r.message['account_type'] == "Bank" ? 1 : 0));
									if(!frm.doc.received_amount && frm.doc.paid_amount)
										frm.events.paid_amount(frm);
								} else if(frm.doc.payment_type=="Pay" && currency_field=="paid_from_account_currency") {
									frm.toggle_reqd(["reference_no", "reference_date"],
										(r.message['account_type'] == "Bank" ? 1 : 0));

									if(!frm.doc.paid_amount && frm.doc.received_amount)
										frm.events.received_amount(frm);
								}
							},
							() => {
								if(callback_function) callback_function(frm);

								frm.events.hide_unhide_fields(frm);
								frm.events.set_dynamic_labels(frm);
							}
						]);
					}
				}
			});
		}
	},

	paid_from_account_currency: function(frm) {
		if(!frm.doc.paid_from_account_currency) return;
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

		if (frm.doc.paid_from_account_currency == company_currency) {
			frm.set_value("source_exchange_rate", 1);
		} else if (frm.doc.paid_from){
			if (in_list(["Internal Transfer", "Pay"], frm.doc.payment_type)) {
				var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
				frappe.call({
					method: "erpnext.setup.utils.get_exchange_rate",
					args: {
						from_currency: frm.doc.paid_from_account_currency,
						to_currency: company_currency,
						transaction_date: frm.doc.posting_date
					},
					callback: function(r, rt) {
						frm.set_value("source_exchange_rate", r.message);
					}
				})
			} else {
				frm.events.set_current_exchange_rate(frm, "source_exchange_rate",
					frm.doc.paid_from_account_currency, company_currency);
			}
		}
	},

	paid_to_account_currency: function(frm) {
		if(!frm.doc.paid_to_account_currency) return;
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

		frm.events.set_current_exchange_rate(frm, "target_exchange_rate",
			frm.doc.paid_to_account_currency, company_currency);
	},

	set_current_exchange_rate: function(frm, exchange_rate_field, from_currency, to_currency) {
		frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				transaction_date: frm.doc.posting_date,
				from_currency: from_currency,
				to_currency: to_currency
			},
			callback: function(r, rt) {
				frm.set_value(exchange_rate_field, r.message);
			}
		})
	},

	posting_date: function(frm) {
		frm.events.paid_from_account_currency(frm);
	},

	source_exchange_rate: function(frm) {
		if (frm.doc.paid_amount) {
			frm.set_value("base_paid_amount", flt(frm.doc.paid_amount) * flt(frm.doc.source_exchange_rate));
			if(!frm.set_paid_amount_based_on_received_amount &&
					(frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency)) {
				frm.set_value("target_exchange_rate", frm.doc.source_exchange_rate);
				frm.set_value("base_received_amount", frm.doc.base_paid_amount);
			}

			frm.events.set_unallocated_amount(frm);
		}

		// Make read only if Accounts Settings doesn't allow stale rates
		frm.set_df_property("source_exchange_rate", "read_only", erpnext.stale_rate_allowed() ? 0 : 1);
	},

	target_exchange_rate: function(frm) {
		frm.set_paid_amount_based_on_received_amount = true;

		if (frm.doc.received_amount) {
			frm.set_value("base_received_amount",
				flt(frm.doc.received_amount) * flt(frm.doc.target_exchange_rate));

			if(!frm.doc.source_exchange_rate &&
					(frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency)) {
				frm.set_value("source_exchange_rate", frm.doc.target_exchange_rate);
				frm.set_value("base_paid_amount", frm.doc.base_received_amount);
			}

			frm.events.set_unallocated_amount(frm);
		}
		frm.set_paid_amount_based_on_received_amount = false;

		// Make read only if Accounts Settings doesn't allow stale rates
		frm.set_df_property("target_exchange_rate", "read_only", erpnext.stale_rate_allowed() ? 0 : 1);
	},

	paid_amount: function(frm) {
		frm.set_value("base_paid_amount", flt(frm.doc.paid_amount) * flt(frm.doc.source_exchange_rate));
		frm.trigger("reset_received_amount");
		frm.events.hide_unhide_fields(frm);
	},

	received_amount: function(frm) {
		frm.set_paid_amount_based_on_received_amount = true;

		if(!frm.doc.paid_amount && frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency) {
			frm.set_value("paid_amount", frm.doc.received_amount);

			if(frm.doc.target_exchange_rate) {
				frm.set_value("source_exchange_rate", frm.doc.target_exchange_rate);
			}
			frm.set_value("base_paid_amount", frm.doc.base_received_amount);
		}

		frm.set_value("base_received_amount",
			flt(frm.doc.received_amount) * flt(frm.doc.target_exchange_rate));

		if(frm.doc.payment_type == "Pay")
			frm.events.allocate_party_amount_against_ref_docs(frm, frm.doc.received_amount);
		else
			frm.events.set_unallocated_amount(frm);

		frm.set_paid_amount_based_on_received_amount = false;
		frm.events.hide_unhide_fields(frm);
	},

	reset_received_amount: function(frm) {
		if(!frm.set_paid_amount_based_on_received_amount &&
				(frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency)) {

			frm.set_value("received_amount", frm.doc.paid_amount);

			if(frm.doc.source_exchange_rate) {
				frm.set_value("target_exchange_rate", frm.doc.source_exchange_rate);
			}
			frm.set_value("base_received_amount", frm.doc.base_paid_amount);
		}

		if(frm.doc.payment_type == "Receive")
			frm.events.allocate_party_amount_against_ref_docs(frm, frm.doc.paid_amount);
		else
			frm.events.set_unallocated_amount(frm);
	},

	get_outstanding_invoice: function(frm) {
		const today = frappe.datetime.get_today();
		const fields = [
			{fieldtype:"Section Break", label: __("Posting Date")},
			{fieldtype:"Date", label: __("From Date"),
				fieldname:"from_posting_date", default:frappe.datetime.add_days(today, -30)},
			{fieldtype:"Column Break"},
			{fieldtype:"Date", label: __("To Date"), fieldname:"to_posting_date", default:today},
			{fieldtype:"Section Break", label: __("Due Date")},
			{fieldtype:"Date", label: __("From Date"), fieldname:"from_due_date"},
			{fieldtype:"Column Break"},
			{fieldtype:"Date", label: __("To Date"), fieldname:"to_due_date"},
			{fieldtype:"Section Break", label: __("Outstanding Amount")},
			{fieldtype:"Float", label: __("Greater Than Amount"),
				fieldname:"outstanding_amt_greater_than", default: 0},
			{fieldtype:"Column Break"},
			{fieldtype:"Float", label: __("Less Than Amount"), fieldname:"outstanding_amt_less_than"},
			{fieldtype:"Section Break"},
			{fieldtype:"Check", label: __("Allocate Payment Amount"), fieldname:"allocate_payment_amount", default:1},
		];

		frappe.prompt(fields, function(filters){
			frappe.flags.allocate_payment_amount = true;
			frm.events.validate_filters_data(frm, filters);
			frm.events.get_outstanding_documents(frm, filters);
		}, __("Filters"), __("Get Outstanding Documents"));
	},

	validate_filters_data: function(frm, filters) {
		const fields = {
			'Posting Date': ['from_posting_date', 'to_posting_date'],
			'Due Date': ['from_posting_date', 'to_posting_date'],
			'Advance Amount': ['from_posting_date', 'to_posting_date'],
		};

		for (let key in fields) {
			let from_field = fields[key][0];
			let to_field = fields[key][1];

			if (filters[from_field] && !filters[to_field]) {
				frappe.throw(__("Error: {0} is mandatory field",
					[to_field.replace(/_/g, " ")]
				));
			} else if (filters[from_field] && filters[from_field] > filters[to_field]) {
				frappe.throw(__("{0}: {1} must be less than {2}",
					[key, from_field.replace(/_/g, " "), to_field.replace(/_/g, " ")]
				));
			}
		}
	},

	get_outstanding_documents: function(frm, filters) {
		frm.clear_table("references");

		if(!frm.doc.party) {
			return;
		}

		frm.events.check_mandatory_to_fetch(frm);
		var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

		var args = {
			"posting_date": frm.doc.posting_date,
			"company": frm.doc.company,
			"party_type": frm.doc.party_type,
			"payment_type": frm.doc.payment_type,
			"party": frm.doc.party,
			"party_account": frm.doc.payment_type=="Receive" ? frm.doc.paid_from : frm.doc.paid_to,
			"cost_center": frm.doc.cost_center
		}

		for (let key in filters) {
			args[key] = filters[key];
		}

		frappe.flags.allocate_payment_amount = filters['allocate_payment_amount'];

		return  frappe.call({
			method: 'erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding_reference_documents',
			args: {
				args:args
			},
			callback: function(r, rt) {
				if(r.message) {
					var total_positive_outstanding = 0;
					var total_negative_outstanding = 0;

					$.each(r.message, function(i, d) {
						var c = frm.add_child("references");
						c.reference_doctype = d.voucher_type;
						c.reference_name = d.voucher_no;
						c.due_date = d.due_date
						c.total_amount = d.invoice_amount;
						c.outstanding_amount = d.outstanding_amount;
						c.bill_no = d.bill_no;

						if(!in_list(["Sales Order", "Purchase Order", "Expense Claim", "Fees"], d.voucher_type)) {
							if(flt(d.outstanding_amount) > 0)
								total_positive_outstanding += flt(d.outstanding_amount);
							else
								total_negative_outstanding += Math.abs(flt(d.outstanding_amount));
						}

						var party_account_currency = frm.doc.payment_type=="Receive" ?
							frm.doc.paid_from_account_currency : frm.doc.paid_to_account_currency;

						if(party_account_currency != company_currency) {
							c.exchange_rate = d.exchange_rate;
						} else {
							c.exchange_rate = 1;
						}
						if (in_list(['Sales Invoice', 'Purchase Invoice', "Expense Claim", "Fees"], d.reference_doctype)){
							c.due_date = d.due_date;
						}
					});

					if(
						(frm.doc.payment_type=="Receive" && frm.doc.party_type=="Customer") ||
						(frm.doc.payment_type=="Pay" && frm.doc.party_type=="Supplier")  ||
						(frm.doc.payment_type=="Pay" && frm.doc.party_type=="Employee") ||
						(frm.doc.payment_type=="Receive" && frm.doc.party_type=="Student")
					) {
						if(total_positive_outstanding > total_negative_outstanding)
							if (!frm.doc.paid_amount)
								frm.set_value("paid_amount",
									total_positive_outstanding - total_negative_outstanding);
					} else if (
						total_negative_outstanding &&
						total_positive_outstanding < total_negative_outstanding
					) {
						if (!frm.doc.received_amount)
							frm.set_value("received_amount",
								total_negative_outstanding - total_positive_outstanding);
					}
				}

				frm.events.allocate_party_amount_against_ref_docs(frm,
					(frm.doc.payment_type=="Receive" ? frm.doc.paid_amount : frm.doc.received_amount));

			}
		});
	},

	allocate_party_amount_against_ref_docs: function(frm, paid_amount) {
		var total_positive_outstanding_including_order = 0;
		var total_negative_outstanding = 0;
		var total_deductions = frappe.utils.sum($.map(frm.doc.deductions || [],
			function(d) { return flt(d.amount) }));

		paid_amount -= total_deductions;

		$.each(frm.doc.references || [], function(i, row) {
			if(flt(row.outstanding_amount) > 0)
				total_positive_outstanding_including_order += flt(row.outstanding_amount);
			else
				total_negative_outstanding += Math.abs(flt(row.outstanding_amount));
		})

		var allocated_negative_outstanding = 0;
		if (
				(frm.doc.payment_type=="Receive" && frm.doc.party_type=="Customer") ||
				(frm.doc.payment_type=="Pay" && frm.doc.party_type=="Supplier") ||
				(frm.doc.payment_type=="Pay" && frm.doc.party_type=="Employee") ||
				(frm.doc.payment_type=="Receive" && frm.doc.party_type=="Student")
			) {
				if(total_positive_outstanding_including_order > paid_amount) {
					var remaining_outstanding = total_positive_outstanding_including_order - paid_amount;
					allocated_negative_outstanding = total_negative_outstanding < remaining_outstanding ?
						total_negative_outstanding : remaining_outstanding;
			}

			var allocated_positive_outstanding =  paid_amount + allocated_negative_outstanding;
		} else if (in_list(["Customer", "Supplier"], frm.doc.party_type)) {
			if(paid_amount > total_negative_outstanding) {
				if(total_negative_outstanding == 0) {
					frappe.msgprint(__("Cannot {0} {1} {2} without any negative outstanding invoice",
						[frm.doc.payment_type,
							(frm.doc.party_type=="Customer" ? "to" : "from"), frm.doc.party_type]));
					return false
				} else {
					frappe.msgprint(__("Paid Amount cannot be greater than total negative outstanding amount {0}", [total_negative_outstanding]));
					return false;
				}
			} else {
				allocated_positive_outstanding = total_negative_outstanding - paid_amount;
				allocated_negative_outstanding = paid_amount +
					(total_positive_outstanding_including_order < allocated_positive_outstanding ?
						total_positive_outstanding_including_order : allocated_positive_outstanding)
			}
		}

		$.each(frm.doc.references || [], function(i, row) {
			row.allocated_amount = 0 //If allocate payment amount checkbox is unchecked, set zero to allocate amount
			if(frappe.flags.allocate_payment_amount != 0){
				if(row.outstanding_amount > 0 && allocated_positive_outstanding > 0) {
					if(row.outstanding_amount >= allocated_positive_outstanding) {
						row.allocated_amount = allocated_positive_outstanding;
					} else {
						row.allocated_amount = row.outstanding_amount;
					}

					allocated_positive_outstanding -= flt(row.allocated_amount);
				} else if (row.outstanding_amount < 0 && allocated_negative_outstanding) {
					if(Math.abs(row.outstanding_amount) >= allocated_negative_outstanding)
						row.allocated_amount = -1*allocated_negative_outstanding;
					else row.allocated_amount = row.outstanding_amount;

					allocated_negative_outstanding -= Math.abs(flt(row.allocated_amount));
				}
			}
		})

		frm.refresh_fields()
		frm.events.set_total_allocated_amount(frm);
	},

	set_total_allocated_amount: function(frm) {
		var total_allocated_amount = 0.0;
		var base_total_allocated_amount = 0.0;
		$.each(frm.doc.references || [], function(i, row) {
			if (row.allocated_amount) {
				total_allocated_amount += flt(row.allocated_amount);
				base_total_allocated_amount += flt(flt(row.allocated_amount)*flt(row.exchange_rate),
					precision("base_paid_amount"));
			}
		});
		frm.set_value("total_allocated_amount", Math.abs(total_allocated_amount));
		frm.set_value("base_total_allocated_amount", Math.abs(base_total_allocated_amount));

		frm.events.set_unallocated_amount(frm);
	},

	set_unallocated_amount: function(frm) {
		var unallocated_amount = 0;
		var total_deductions = frappe.utils.sum($.map(frm.doc.deductions || [],
			function(d) { return flt(d.amount) }));

		if(frm.doc.party) {
			if(frm.doc.payment_type == "Receive"
				&& frm.doc.base_total_allocated_amount < frm.doc.base_received_amount + total_deductions
				&& frm.doc.total_allocated_amount < frm.doc.paid_amount + (total_deductions / frm.doc.source_exchange_rate)) {
					unallocated_amount = (frm.doc.base_received_amount + total_deductions
						- frm.doc.base_total_allocated_amount) / frm.doc.source_exchange_rate;
			} else if (frm.doc.payment_type == "Pay"
				&& frm.doc.base_total_allocated_amount < frm.doc.base_paid_amount - total_deductions
				&& frm.doc.total_allocated_amount < frm.doc.received_amount + (total_deductions / frm.doc.target_exchange_rate)) {
					unallocated_amount = (frm.doc.base_paid_amount - (total_deductions
						+ frm.doc.base_total_allocated_amount)) / frm.doc.target_exchange_rate;
			}
		}
		frm.set_value("unallocated_amount", unallocated_amount);
		frm.trigger("set_difference_amount");
	},

	set_difference_amount: function(frm) {
		var difference_amount = 0;
		var base_unallocated_amount = flt(frm.doc.unallocated_amount) *
			(frm.doc.payment_type=="Receive" ? frm.doc.source_exchange_rate : frm.doc.target_exchange_rate);

		var base_party_amount = flt(frm.doc.base_total_allocated_amount) + base_unallocated_amount;

		if(frm.doc.payment_type == "Receive") {
			difference_amount = base_party_amount - flt(frm.doc.base_received_amount);
		} else if (frm.doc.payment_type == "Pay") {
			difference_amount = flt(frm.doc.base_paid_amount) - base_party_amount;
		} else {
			difference_amount = flt(frm.doc.base_paid_amount) - flt(frm.doc.base_received_amount);
		}

		var total_deductions = frappe.utils.sum($.map(frm.doc.deductions || [],
			function(d) { return flt(d.amount) }));

		frm.set_value("difference_amount", difference_amount - total_deductions);

		frm.events.hide_unhide_fields(frm);
	},

	unallocated_amount: function(frm) {
		frm.trigger("set_difference_amount");
	},

	check_mandatory_to_fetch: function(frm) {
		$.each(["Company", "Party Type", "Party", "payment_type"], function(i, field) {
			if(!frm.doc[frappe.model.scrub(field)]) {
				frappe.msgprint(__("Please select {0} first", [field]));
				return false;
			}

		});
	},

	validate_reference_document: function(frm, row) {
		var _validate = function(i, row) {
			if (!row.reference_doctype) {
				return;
			}

			if(frm.doc.party_type=="Customer" &&
				!in_list(["Sales Order", "Sales Invoice", "Journal Entry"], row.reference_doctype)
			) {
				frappe.model.set_value(row.doctype, row.name, "reference_doctype", null);
				frappe.msgprint(__("Row #{0}: Reference Document Type must be one of Sales Order, Sales Invoice or Journal Entry", [row.idx]));
				return false;
			}

			if(frm.doc.party_type=="Supplier" &&
				!in_list(["Purchase Order", "Purchase Invoice", "Journal Entry"], row.reference_doctype)
			) {
				frappe.model.set_value(row.doctype, row.name, "against_voucher_type", null);
				frappe.msgprint(__("Row #{0}: Reference Document Type must be one of Purchase Order, Purchase Invoice or Journal Entry", [row.idx]));
				return false;
			}

			if(frm.doc.party_type=="Employee" &&
				!in_list(["Expense Claim", "Journal Entry"], row.reference_doctype)
			) {
				frappe.model.set_value(row.doctype, row.name, "against_voucher_type", null);
				frappe.msgprint(__("Row #{0}: Reference Document Type must be one of Expense Claim or Journal Entry", [row.idx]));
				return false;
			}
		}

		if (row) {
			_validate(0, row);
		} else {
			$.each(frm.doc.vouchers || [], _validate);
		}
	},

	write_off_difference_amount: function(frm) {
		frm.events.set_deductions_entry(frm, "write_off_account");
	},

	set_exchange_gain_loss: function(frm) {
		frm.events.set_deductions_entry(frm, "exchange_gain_loss_account");
	},

	set_deductions_entry: function(frm, account) {
		if(frm.doc.difference_amount) {
			frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_company_defaults",
				args: {
					company: frm.doc.company
				},
				callback: function(r, rt) {
					if(r.message) {
						var write_off_row = $.map(frm.doc["deductions"] || [], function(t) {
							return t.account==r.message[account] ? t : null; });

						var row = [];

						var difference_amount = flt(frm.doc.difference_amount,
							precision("difference_amount"));

						if (!write_off_row.length && difference_amount) {
							row = frm.add_child("deductions");
							row.account = r.message[account];
							row.cost_center = r.message["cost_center"];
						} else {
							row = write_off_row[0];
						}

						if (row) {
							row.amount = flt(row.amount) + difference_amount;
						} else {
							frappe.msgprint(__("No gain or loss in the exchange rate"))
						}

						refresh_field("deductions");

						frm.events.set_unallocated_amount(frm);
					}
				}
			})
		}
	},

	bank_account: function(frm) {
		const field = frm.doc.payment_type == "Pay" ? "paid_from":"paid_to";
		if (frm.doc.bank_account && in_list(['Pay', 'Receive'], frm.doc.payment_type)) {
			frappe.call({
				method: "erpnext.accounts.doctype.bank_account.bank_account.get_bank_account_details",
				args: {
					bank_account: frm.doc.bank_account
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value(field, r.message.account);
						frm.set_value('bank', r.message.bank);
						frm.set_value('bank_account_no', r.message.bank_account_no);
					}
				}
			});
		}
	}
});


frappe.ui.form.on('Payment Entry Reference', {
	reference_doctype: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frm.events.validate_reference_document(frm, row);
	},

	reference_name: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.reference_name && row.reference_doctype) {
			return frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_reference_details",
				args: {
					reference_doctype: row.reference_doctype,
					reference_name: row.reference_name,
					party_account_currency: frm.doc.payment_type=="Receive" ?
						frm.doc.paid_from_account_currency : frm.doc.paid_to_account_currency
				},
				callback: function(r, rt) {
					if(r.message) {
						$.each(r.message, function(field, value) {
							frappe.model.set_value(cdt, cdn, field, value);
						})

						let allocated_amount = frm.doc.unallocated_amount > row.outstanding_amount ?
							row.outstanding_amount : frm.doc.unallocated_amount;

						frappe.model.set_value(cdt, cdn, 'allocated_amount', allocated_amount);
						frm.refresh_fields();
					}
				}
			})
		}
	},

	allocated_amount: function(frm) {
		frm.events.set_total_allocated_amount(frm);
	},

	references_remove: function(frm) {
		frm.events.set_total_allocated_amount(frm);
	}
})

frappe.ui.form.on('Payment Entry Deduction', {
	amount: function(frm) {
		frm.events.set_unallocated_amount(frm);
	},

	deductions_remove: function(frm) {
		frm.events.set_unallocated_amount(frm);
	}
})
frappe.ui.form.on('Payment Entry', {
	cost_center: function(frm){
		if (frm.doc.posting_date && (frm.doc.paid_from||frm.doc.paid_to)) {
			return frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_party_and_account_balance",
				args: {
					company: frm.doc.company,
					date: frm.doc.posting_date,
					paid_from: frm.doc.paid_from,
					paid_to: frm.doc.paid_to,
					ptype: frm.doc.party_type,
					pty: frm.doc.party,
					cost_center: frm.doc.cost_center
				},
				callback: function(r, rt) {
					if(r.message) {
						frappe.run_serially([
							() => {
								frm.set_value("paid_from_account_balance", r.message.paid_from_account_balance);
								frm.set_value("paid_to_account_balance", r.message.paid_to_account_balance);
								frm.set_value("party_balance", r.message.party_balance);
							},
							() => {
								if(frm.doc.payment_type != "Internal") {
									frm.clear_table("references");
								}
							}
						]);

					}
				}
			});
		}
	},
})