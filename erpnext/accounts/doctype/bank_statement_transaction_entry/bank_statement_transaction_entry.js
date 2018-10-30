// Copyright (c) 2017, sathishpy@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Statement Transaction Entry', {
	setup: function(frm) {
		frm.events.account_filters(frm)
		frm.events.invoice_filter(frm)
	},
	refresh: function(frm) {
		frm.set_df_property("bank_account", "read_only", frm.doc.__islocal ? 0 : 1);
		frm.set_df_property("from_date", "read_only", frm.doc.__islocal ? 0 : 1);
		frm.set_df_property("to_date", "read_only", frm.doc.__islocal ? 0 : 1);
	},
	invoke_doc_function(frm, method) {
		frappe.call({
			doc: frm.doc,
			method: method,
			callback: function(r) {
				if(!r.exe) {
					frm.refresh_fields();
				}
			}
		});
	},
	account_filters: function(frm) {
		frm.fields_dict['bank_account'].get_query = function(doc, dt, dn) {
			return {
				filters:[
					["Account", "account_type", "in", ["Bank"]]
				]
			}
		};
		frm.fields_dict['receivable_account'].get_query = function(doc, dt, dn) {
			return {
				filters: {"account_type": "Receivable"}
			}
		};
		frm.fields_dict['payable_account'].get_query = function(doc, dt, dn) {
			return {
				filters: {"account_type": "Payable"}
			}
		};
	},

	invoice_filter: function(frm) {
		frm.set_query("invoice", "payment_invoice_items", function(doc, cdt, cdn) {
			let row = locals[cdt][cdn]
			if (row.party_type == "Customer") {
				return {
					filters:[[row.invoice_type, "customer", "in", [row.party]],
									[row.invoice_type, "status", "!=", "Cancelled" ],
									[row.invoice_type, "posting_date", "<", row.transaction_date ],
									[row.invoice_type, "outstanding_amount", ">", 0 ]]
				}
			} else if (row.party_type == "Supplier") {
				return {
					filters:[[row.invoice_type, "supplier", "in", [row.party]],
									[row.invoice_type, "status", "!=", "Cancelled" ],
									[row.invoice_type, "posting_date", "<", row.transaction_date ],
									[row.invoice_type, "outstanding_amount", ">", 0 ]]
				}
			}
		});
	},

	match_invoices: function(frm) {
		frm.events.invoke_doc_function(frm, "populate_matching_invoices");
	},
	create_payments: function(frm) {
		frm.events.invoke_doc_function(frm, "create_payment_entries");
	},
	submit_payments: function(frm) {
		frm.events.invoke_doc_function(frm, "submit_payment_entries");
	},
});


frappe.ui.form.on('Bank Statement Transaction Invoice Item', {
	party_type: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.party_type == "Customer") {
			row.invoice_type = "Sales Invoice";
		} else if (row.party_type == "Supplier") {
			row.invoice_type = "Purchase Invoice";
		} else if (row.party_type == "Account") {
			row.invoice_type = "Journal Entry";
		}
		refresh_field("invoice_type", row.name, "payment_invoice_items");

	},
	invoice_type: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.invoice_type == "Purchase Invoice") {
			row.party_type = "Supplier";
		} else if (row.invoice_type == "Sales Invoice") {
			row.party_type = "Customer";
		}
		refresh_field("party_type", row.name, "payment_invoice_items");
	}
});