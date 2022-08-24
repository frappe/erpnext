// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Credit Note CXP', {
	// refresh: function(frm) {

	// }
	setup: function(frm) {
		frm.set_query("reference_doctype", "references", function() {
			var doctypes = ["Purchase Invoice", "Supplier Documents", "Debit Note CXP"];

			return {
				filters: { "name": ["in", doctypes] }
			};
		});

		frm.set_query("reference_name", "references", function(doc, cdt, cdn) {
			const filters = {"docstatus": 1,"outstanding_amount": [">","0"], "supplier": doc.supplier};
			// if(reference_name == "Purchase Invoice"){

			// }

			// const filters = {"docstatus": 1};

			return {
				filters: filters
			};
		});
    },
});
