// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/loan_management/loan_common.js' %};

frappe.ui.form.on('Loan Disbursement', {
	refresh: function(frm) {
		frm.set_query('against_loan', function() {
			return {
				'filters': {
					'docstatus': 1,
					'status': 'Sanctioned'
				}
			}
		})
	},
	disbursement_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.disbursement_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("disbursement_date_nepal", resp.message)
				}
			}
		})
	},
	reference_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.reference_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("reference_date_nepal", resp.message)
				}
			}
		})
	},
});
