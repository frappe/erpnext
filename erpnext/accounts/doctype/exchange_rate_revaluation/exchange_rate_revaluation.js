// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exchange Rate Revaluation', {
	setup: function(frm) {
		frm.set_query("party_type", "accounts", function() {
			return {
				"filters": {
					"name": ["in", Object.keys(frappe.boot.party_account_types)],
				}
			};
		});
		frm.set_query("account", "accounts", function(doc) {
			return {
				"filters": {
					"company": doc.company
				}
			};
		});
	},

	refresh: function(frm) {
		if(frm.doc.docstatus==1) {
			frm.add_custom_button(__('Make Journal Entry'), function() {
				return frm.events.make_jv(frm);
			});
		}
	},

	get_entries: function(frm) {
		frappe.call({
			method: "get_accounts_data",
			doc: cur_frm.doc,
			callback: function(r){
				frappe.model.clear_table(frm.doc, "accounts");
				if(r.message) {
					r.message.forEach((d) => {
						cur_frm.add_child("accounts",d);
					});
					frm.events.get_total_gain_loss(frm);
					refresh_field("accounts");
				}
			}
		});
	},

	get_total_gain_loss: function(frm) {
		if(!(frm.doc.accounts && frm.doc.accounts.length)) return;

		let total_gain_loss = 0;
		frm.doc.accounts.forEach((d) => {
			d.gain_loss = flt(d.new_balance_in_base_currency, precision("new_balance_in_base_currency", d)) - flt(d.balance_in_base_currency, precision("balance_in_base_currency", d));
			total_gain_loss += flt(d.gain_loss, precision("gain_loss", d));
		});
		
		frm.set_value("total_gain_loss", flt(total_gain_loss, precision("total_gain_loss")));
		frm.refresh_fields();
	},

	make_jv : function(frm) {
		frappe.call({
			method: "make_jv_entry",
			doc: frm.doc,
			callback: function(r){
				if (r.message) {
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
				}
			}
		});
	}
});

frappe.ui.form.on("Exchange Rate Revaluation Account", {
	new_exchange_rate: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		row.new_balance_in_base_currency = flt(row.new_exchange_rate * flt(row.balance_in_account_currency),
			precision("new_balance_in_base_currency", row));
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency);
		refresh_field("accounts");
		frm.events.get_total_gain_loss(frm);
	},

	account: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.account) {
			get_account_details(frm, cdt, cdn);
		}
	},

	party: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.party && row.account) {
			get_account_details(frm, cdt, cdn);
		}
	},

	accounts_remove: function(frm) {
		frm.events.get_total_gain_loss(frm);
	}
});

var get_account_details = function(frm, cdt, cdn) {
	var row = frappe.get_doc(cdt, cdn);
	if(!frm.doc.company || !frm.doc.posting_date) {
		frappe.throw(__("Please select Company and Posting Date to getting entries"));
	}
	frappe.call({
		method: "erpnext.accounts.doctype.exchange_rate_revaluation.exchange_rate_revaluation.get_account_details",
		args:{
			account: row.account,
			company: frm.doc.company,
			posting_date: frm.doc.posting_date,
			party_type: row.party_type,
			party: row.party
		},
		callback: function(r){
			$.extend(row, r.message);
			refresh_field("accounts");
			frm.events.get_total_gain_loss(frm);
		}
	});
};