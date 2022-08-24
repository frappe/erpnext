// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cancel Bank Checks', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		cur_frm.fields_dict['check'].get_query = function(doc, cdt, cdn) {
			return {
				filters:{'check': 1, 'cancel': 0, 'status': ["!=","Reconciled"], 'bank_account': doc.bank_account}
			}
		}
	}
});
