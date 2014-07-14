// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts");

erpnext.accounts.PaymentReconciliationController = frappe.ui.form.Controller.extend({

	onload: function() {
		var me = this
		this.frm.set_query ('party_account', function() {
			return{
				filters:[
					['Account', 'company', '=', me.frm.doc.company],
					['Account', 'group_or_ledger', '=', 'Ledger'],
					['Account', 'master_type', 'in', ['Customer', 'Supplier']]
				]
			};
		});
	},

	get_unreconciled_entries: function() {
		var me = this;
		if (!this.frm.doc.company) {
			msgprint(__("Please enter the Company"));
		} 
		else if (!this.frm.doc.party_account) {
			msgprint(__("Please enter the Party Account"));			
		}
		else {
			return this.frm.call({
				doc: me.frm.doc,
				method: 'get_unreconciled_entries'
			});
		}
	}

});

$.extend(cur_frm.cscript, new erpnext.accounts.PaymentReconciliationController({frm: cur_frm}));

cur_frm.add_fetch('party_account', 'master_type', 'party_type')