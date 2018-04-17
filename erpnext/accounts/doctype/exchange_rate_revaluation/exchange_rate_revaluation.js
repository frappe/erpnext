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