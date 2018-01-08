// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.share_transfer");

frappe.ui.form.on('Share Transfer', {
	refresh: function(frm) {
	},
	transfer_type: (frm) => {
		if (frm.doc.transfer_type == 'Purchase'){
			frm.doc.to_party = '';
			frm.refresh_field("to_party");
			frm.fields_dict.to_party.$wrapper.hide();
			frm.fields_dict.to_folio_no.$wrapper.hide();
			frm.fields_dict.from_party.$wrapper.show();
			frm.fields_dict.from_folio_no.$wrapper.show();
		} else if (frm.doc.transfer_type == 'Issue') {
			frm.doc.from_party = '';
			frm.refresh_field("from_party");
			frm.fields_dict.from_party.$wrapper.hide();
			frm.fields_dict.from_folio_no.$wrapper.hide();
			frm.fields_dict.to_party.$wrapper.show();
			frm.fields_dict.to_folio_no.$wrapper.show();
		} else if (frm.doc.transfer_type == 'Transfer') {
			frm.fields_dict.from_party.$wrapper.show();
			frm.fields_dict.from_folio_no.$wrapper.show();
			frm.fields_dict.to_party.$wrapper.show();
			frm.fields_dict.to_folio_no.$wrapper.show();
		}
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