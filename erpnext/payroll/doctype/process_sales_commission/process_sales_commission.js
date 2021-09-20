// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Process Sales Commission', {
	setup: function(frm){
		frm.set_query("department", function() {
			if (!frm.doc.company) {
				frappe.throw(__("Please select company first"))
			}
			return {
				filters: {
					company: frm.doc.company
				}
			}
		});
	},
});
