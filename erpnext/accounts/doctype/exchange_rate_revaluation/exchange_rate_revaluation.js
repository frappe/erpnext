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
			}
		});
	},
});

frappe.ui.form.on("Exchange Rate Revaluation Account", {
	new_exchange_rate: function(frm, cdt, cdn) {
		$.each(frm.doc.exchange_rate_revaluation_account, function(i, d) {
			var me = frm.doc.exchange_rate_revaluation_account[i];
			me.new_balance_in_base_currency = me.new_exchange_rate * me.balance_in_alternate_currency;
			me.difference = me.new_balance_in_base_currency - me.balance_in_base_currency;
		});
		refresh_field("exchange_rate_revaluation_account");
	}
});