// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accounting Dimension', {

	document_type: function(frm){
		frm.set_value('label', frm.doc.document_type);
		frm.set_value('fieldname', frappe.scrub(frm.doc.document_type))

		frappe.db.get_value('Accounting Dimension', {'document_type': frm.doc.document_type}, 'document_type', (r) => {
			if (r.document_type) {
				frm.set_df_property('document_type', 'description', "Document type is already set as dimension");
			}
		});
	},
});
