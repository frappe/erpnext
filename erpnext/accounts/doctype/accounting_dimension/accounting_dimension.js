// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accounting Dimension', {

	refresh: function(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('Show {0}', [frm.doc.document_type]), function () {
				frappe.set_route("List", frm.doc.document_type);
			});
		}
	},

	document_type: function(frm) {
		frm.set_value('label', frm.doc.document_type);
		frm.set_value('fieldname', frappe.scrub(frm.doc.document_type));

		frappe.db.get_value('Accounting Dimension', {'document_type': frm.doc.document_type}, 'document_type', (r) => {
			if (r.document_type) {
				frm.set_df_property('document_type', 'description', "Document type is already set as dimension");
			}
		});
	},

	disabled: function(frm) {
		frappe.call({
			method: "erpnext.accounts.doctype.accounting_dimension.accounting_dimension.disable_dimension",
			args: {
				doc: frm.doc
			}
		});
	}
});
