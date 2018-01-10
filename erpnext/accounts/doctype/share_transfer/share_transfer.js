// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.share_transfer");

frappe.ui.form.on('Share Transfer', {
	refresh: function(frm) {
		// Don't show Parties which are a Company
		let parties = ['from_party', 'to_party'];
		parties.forEach((party) => {
			frm.fields_dict[party].get_query = function() {
				return {
					filters: [
						["Shareholder Party", "is_company", "=", 0]
					]
				};
			};
		});
	},
	no_of_shares: (frm) => {
		if (frm.doc.rate != undefined || frm.doc.rate != null){
			erpnext.share_transfer.update_amount(frm);
		}
	},
	rate: (frm) => {
		if (frm.doc.no_of_shares != undefined || frm.doc.no_of_shares != null){
			erpnext.share_transfer.update_amount(frm);
		}
	}
});

erpnext.share_transfer.update_amount = function(frm) {
	frm.doc.amount = frm.doc.no_of_shares * frm.doc.rate;
	frm.refresh_field("amount");
};
