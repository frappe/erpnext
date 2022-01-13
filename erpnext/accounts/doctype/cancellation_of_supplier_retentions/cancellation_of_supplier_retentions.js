// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cancellation Of Supplier Retentions', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		cur_frm.fields_dict['supplier_retention'].get_query = function(doc, cdt, cdn) {
			return {
				filters:{'docstatus': 1}
			}
		}
	},
});
