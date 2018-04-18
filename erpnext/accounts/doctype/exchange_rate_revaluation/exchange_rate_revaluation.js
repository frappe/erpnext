// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exchange Rate Revaluation', {
	refresh: function(frm) {
	},

	get_entries: function(frm) {
		frappe.call({
			method: "get_accounts_data",
			doc: cur_frm.doc,
			callback: function(r){
				frappe.model.clear_table(frm.doc, "exchange_rate_revaluation_account");
				r.message.forEach((d) => {
					cur_frm.add_child("exchange_rate_revaluation_account",d);
				});
				refresh_field("exchange_rate_revaluation_account");
				frm.events.get_total_gain_loss(frm);
			}
		});
	},

	get_total_gain_loss: function(frm) {
		frm.doc.total_gain_loss = 0;
		frm.doc.exchange_rate_revaluation_account.forEach((d) => {
			frm.doc.total_gain_loss += d.difference;
		});
		refresh_field("total_gain_loss");
	},
});

frappe.ui.form.on("Exchange Rate Revaluation Account", {
	new_exchange_rate: function(frm) {
		frm.doc.exchange_rate_revaluation_account.forEach((d) => {
			d.new_balance_in_base_currency = d.new_exchange_rate * d.balance_in_alternate_currency;
			d.difference = d.new_balance_in_base_currency - d.balance_in_base_currency;
		});
		refresh_field("exchange_rate_revaluation_account");
		frm.events.get_total_gain_loss(frm);
	},

	account: function(frm, cdt, cdn) {
		var row = frappe.get_doc(cdt,cdn);
		console.log("local cdt and cdn",cdn,row.account);
		frappe.call({
			method: "get_accounts_data",
			doc: cur_frm.doc,
			args:{ account:row.account},
			callback: function(r){
				r.message.forEach((d) => {
					row.balance_in_base_currency = d.balance_in_base_currency;
					row.balance_in_alternate_currency = d.balance_in_alternate_currency;
					row.current_exchange_rate = d.current_exchange_rate;
					row.difference = d.difference;
				});
				refresh_field("exchange_rate_revaluation_account");
				frm.events.get_total_gain_loss(frm);
			}
		});
	}
});