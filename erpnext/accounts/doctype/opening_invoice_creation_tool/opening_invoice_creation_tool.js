// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Opening Invoice Creation Tool', {
	setup: function(frm) {
		frm.set_query('party_type', 'invoices', function(doc, cdt, cdn) {
			return {
				filters: {
					'name': ['in', 'Customer,Supplier']
				}
			}
		});
	},

	invoice_type: (frm) => {
		$.each(frm.doc.invoices, (idx, row) => {
			row.party_type = frm.doc.invoice_type == "Sales"? "Customer": "Supplier";
			row.party = "";
		});
		frm.refresh_fields();
	}
});

frappe.ui.form.on('Opening Invoice Creation Tool Item', {
	invoices_add: (frm) => {
		$.each(frm.doc.invoices, (idx, row) => {
			row.party_type = frm.doc.invoice_type == "Sales"? "Customer": "Supplier";
		});
	}
})