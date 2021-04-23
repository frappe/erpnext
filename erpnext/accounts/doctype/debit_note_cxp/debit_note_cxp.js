// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Debit Note CXP', {
	setup: function(frm) {
        frm.set_query("reference_doctype", "references", function() {
			var doctypes = ["Purchase Invoice"];

			return {
				filters: { "name": ["in", doctypes] }
			};
		});

		frm.set_query("reference_name", "references", function(doc, cdt, cdn) {
			const child = locals[cdt][cdn];
			const filters = {"status": 'Unpaid'};
			const party_type_doctypes = ['Purchase Invoice'];
			if (in_list(party_type_doctypes, child.reference_doctype)) {
				filters[doc.party_type.toLowerCase()] = doc.supplier;
			}

			return {
				filters: filters
			};
		});
    },

	amount_references:function(frm, cdt, cdn){
		var d = locals[cdt][cdn];
		debugger
		frappe.model.set_value(d.doctype, d.name, "total_amount", d.total_amount);
		var total = 0;
		debugger
		frm.doc.references.forEach(function(d) { total += d.total_amount; });
		debugger
		frm.set_value("total_references", total);
		frm.refresh_field("total_references");
	},

});
