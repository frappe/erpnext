// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Cashier Closing', {

	expense: function(frm){
		frm.doc.net_amount = frm.doc.expense + frm.doc.in_save - frm.doc.custody;
	},

	custody: function(frm){
		frm.doc.net_amount = frm.doc.expense + frm.doc.in_save - frm.doc.custody;
	},

	in_save: function(frm){
		frm.doc.user = frappe.session.user;
		frm.doc.net_amount = frm.doc.expense + frm.doc.in_save - frm.doc.custody;
	}
});
