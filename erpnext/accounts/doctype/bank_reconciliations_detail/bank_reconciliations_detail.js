// Copyright (c) 2021, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank reconciliations Detail', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		cur_frm.fields_dict['bank_trasaction'].get_query = function(doc, cdt, cdn) {
			return {
				filters:{'status': "Pre-reconciled"}
			}
		}
	}
});