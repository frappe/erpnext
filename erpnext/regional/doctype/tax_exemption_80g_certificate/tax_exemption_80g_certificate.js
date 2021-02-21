// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tax Exemption 80G Certificate', {
	// refresh: function(frm) {

	// },

	get_payments: function(frm) {
		frm.call({
			doc: frm.doc,
			method: 'get_payments',
			freeze: true
		});
	},

	company: function(frm) {
		if (frm.doc.member && frm.doc.company) {
			frm.call({
				doc: frm.doc,
				method: 'set_company_address',
				freeze: true
			});
		}
	}
});
