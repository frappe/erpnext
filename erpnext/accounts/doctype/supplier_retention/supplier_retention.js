// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Supplier Retention', {
	setup: function(frm) {
        frm.set_query("reference_doctype", "references", function() {
			var doctypes = ["Purchase Invoice", "Supplier Documents"];

			return {
				filters: { "name": ["in", doctypes] }
			};
		});

		frm.set_query("reference_name", "references", function(doc, cdt, cdn) {
			const child = locals[cdt][cdn];
			const filters = {"docstatus": 1,"status": ["in", ["Unpaid", "Overdue"]], "company":doc.company};
			const party_type_doctypes = ['Purchase Invoice', 'Supplier Documents'];
			if (in_list(party_type_doctypes, child.reference_doctype)) {
				filters[doc.party_type.toLowerCase()] = doc.supplier;
			}

			return {
				filters: filters
			};
		});

		frm.set_query("reason", "reasons", function(doc, cdt, cdn) {
			const filters = {"company":doc.company};

			return {
				filters: filters
			};
		});
    },
});