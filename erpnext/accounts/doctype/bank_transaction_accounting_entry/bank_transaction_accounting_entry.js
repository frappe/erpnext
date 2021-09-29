// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Transaction Accounting Entry', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		cur_frm.fields_dict['bank_transaction'].get_query = function(doc, cdt, cdn) {
			return {
				filters:{'accounting_seat': 0}
			}
		}
	}
});
