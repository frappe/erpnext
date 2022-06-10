// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Credit Note CXP', {
	// refresh: function(frm) {

	// }
	setup: function(frm) {

		frm.set_query("reference_name", "references", function(doc, cdt, cdn) {
			// const filters = {"docstatus": 1,"status": ["in",["Unpaid", "overdue"]]};
			if(reference_name == "Purchase Invoice"){

			}
			
			const filters = {"docstatus": 1};

			return {
				filters: filters
			};
		});
    },
});
