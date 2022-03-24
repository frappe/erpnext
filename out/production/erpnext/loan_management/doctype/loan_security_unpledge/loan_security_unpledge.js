// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Security Unpledge', {
	refresh: function(frm) {

		if (frm.doc.docstatus == 1 && frm.doc.status == 'Approved') {
			frm.set_df_property('status', 'read_only', 1);
		}
	}
});
