// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tax Exemption 80G Certificate', {
	refresh: function(frm) {
		if (frm.doc.donor) {
			frm.set_query('donation', function() {
				return {
					filters: {
						docstatus: 1,
						donor: frm.doc.donor
					}
				};
			});
		}
	},

	recipient: function(frm) {
		if (frm.doc.recipient === 'Donor') {
			frm.set_value({
				'member': '',
				'member_name': '',
				'member_email': '',
				'member_pan_number': '',
				'fiscal_year': '',
				'total': 0,
				'payments': []
			});
		} else {
			frm.set_value({
				'donor': '',
				'donor_name': '',
				'donor_email': '',
				'donor_pan_number': '',
				'donation': '',
				'date_of_donation': '',
				'amount': 0,
				'mode_of_payment': '',
				'razorpay_payment_id': ''
			});
		}
	},

	get_payments: function(frm) {
		frm.call({
			doc: frm.doc,
			method: 'get_payments',
			freeze: true
		});
	},

	company: function(frm) {
		if ((frm.doc.member || frm.doc.donor) && frm.doc.company) {
			frm.call({
				doc: frm.doc,
				method: 'set_company_address',
				freeze: true
			});
		}
	},

	donation: function(frm) {
		if (frm.doc.recipient === 'Donor' && !frm.doc.donor) {
			frappe.msgprint(__('Please select donor first'));
		}
	}
});
