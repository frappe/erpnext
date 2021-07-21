// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Operation', {
	setup: function(frm) {
		frm.set_query('operation', 'sub_operations', function() {
			return {
				filters: {
					'name': ['not in', [frm.doc.name]]
				}
			};
		});
	}
});