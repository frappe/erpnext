// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Repayment', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		frm.set_query('against_loan', function() {
			return {
				'filters': {
					'docstatus': 1
				}
			};
		});

		if (frm.doc.against_loan && frm.doc.posting_date && frm.doc.docstatus == 0) {
			frm.trigger('calculate_repayment_amounts');
		}
	},

	posting_date : function(frm) {
		frm.trigger('calculate_repayment_amounts');
	},

	against_loan: function(frm) {
		if (frm.doc.posting_date) {
			frm.trigger('calculate_repayment_amounts');
		}
	},

	payment_type: function(frm) {
		if (frm.doc.posting_date) {
			frm.trigger('calculate_repayment_amounts');
		}
	},

	calculate_repayment_amounts: function(frm) {
		frappe.call({
			method: 'erpnext.loan_management.doctype.loan_repayment.loan_repayment.calculate_amounts',
			args: {
				'against_loan': frm.doc.against_loan,
				'posting_date': frm.doc.posting_date,
				'loan_type': frm.doc.loan_type,
				'payment_type': frm.doc.payment_type
			},
			callback: function(r) {
				let amounts = r.message;

				frm.set_value('pending_principal_amount', amounts['principal_amount']);
				if (frm.doc.is_term_loan) {
					frm.set_value('payable_principal_amount', amounts['principal_amount']);
				}
				frm.set_value('interest_payable', amounts['interest_amount']);
				frm.set_value('penalty_amount', amounts['penalty_amount']);
				frm.set_value('payable_amount', amounts['payable_amount']);
			}
		});
	}
});
