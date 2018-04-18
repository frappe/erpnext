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
				refresh_field("exchange_rate_revaluation_account");
				frm.events.get_total_gain_loss(frm);
			}
		});
	},
	get_total_gain_loss: function(frm) {
		frm.doc.total_gain_loss = 0;
		$.each(frm.doc.exchange_rate_revaluation_account, function(i, d) {
			frm.doc.total_gain_loss += d.difference;
		});
		refresh_field("total_gain_loss");
	}
});

frappe.ui.form.on("Exchange Rate Revaluation Account", {
	new_exchange_rate: function(frm, cdt, cdn) {
		$.each(frm.doc.exchange_rate_revaluation_account, function(i, d) {
			d.new_balance_in_base_currency = d.new_exchange_rate * d.balance_in_alternate_currency;
			d.difference = d.new_balance_in_base_currency - d.balance_in_base_currency;
		});
		refresh_field("exchange_rate_revaluation_account");
		frm.events.get_total_gain_loss(frm);
	}
});