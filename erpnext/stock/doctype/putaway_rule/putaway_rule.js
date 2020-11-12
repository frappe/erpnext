// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Putaway Rule', {
	setup: function(frm) {
		frm.set_query("warehouse", function() {
			return {
				"filters": {
					"company": frm.doc.company,
					"is_group": 0
				}
			};
		});
	}
	// refresh: function(frm) {

	// }
});
