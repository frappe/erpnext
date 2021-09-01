// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inventory Download', {
	// refresh: function(frm) {

	// }
	onload: function(frm) {
		var date = new Date;

		cur_frm.fields_dict['warehouse'].get_query = function(doc, cdt, cdn) {
			return {
				filters:{'company': doc.company}
			}
		}
	}
});
