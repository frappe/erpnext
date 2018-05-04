// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exchange Rate Revaluation', {
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

	make_jv : function(frm) {
		frappe.call({
			method: "make_jv_entry",
			doc: cur_frm.doc,
			args:{  "accounts":cur_frm.doc.exchange_rate_revaluation_account,
					"total_gain_loss":cur_frm.doc.total_gain_loss
				 },
			callback: function(r){
				if (r.message)
					var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
			}
		});
	}

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
		frappe.call({
			method: "get_accounts_data",
			doc: cur_frm.doc,
			args:{ account:row.account},
			callback: function(r){
				row.balance_in_base_currency = r.message[0].balance_in_base_currency;
				row.balance_in_alternate_currency = r.message[0].balance_in_alternate_currency;
				row.current_exchange_rate = r.message[0].current_exchange_rate;
				row.difference = r.message[0].difference;
				refresh_field("exchange_rate_revaluation_account");
				frm.events.get_total_gain_loss(frm);
			}
		});
	},

	exchange_rate_revaluation_account_remove: function(frm) {
		frm.events.get_total_gain_loss(frm);
	}
});
