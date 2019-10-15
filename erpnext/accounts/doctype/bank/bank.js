// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank', {
	onload: function(frm) {
		add_fields_to_mapping_table(frm);
	},
	refresh: function(frm) {
		add_fields_to_mapping_table(frm);
	}
});


let add_fields_to_mapping_table = function (frm) {
	let options = [];

	frappe.model.with_doctype("Bank Transaction", function() {
		let meta = frappe.get_meta("Bank Transaction");
		meta.fields.forEach(value => {
			if (!["Section Break", "Column Break"].includes(value.fieldtype)) {
				options.push(value.fieldname);
			}
		});
	});

	frappe.meta.get_docfield("Bank Transaction Mapping", "bank_transaction_field",
		frm.doc.name).options = options;

	frm.fields_dict.bank_transaction_mapping.grid.refresh();
};