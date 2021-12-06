// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Accounting Dimension', {
	refresh: function(frm) {
		frm.set_query('document_type', () => {
			let invalid_doctypes = frappe.model.core_doctypes_list;
			invalid_doctypes.push('Accounting Dimension', 'Project',
				'Cost Center', 'Accounting Dimension Detail', 'Company');

			return {
				filters: {
					name: ['not in', invalid_doctypes]
				}
			};
		});

		if (!frm.is_new()) {
			frm.add_custom_button(__('Show {0}', [frm.doc.document_type]), function () {
				frappe.set_route("List", frm.doc.document_type);
			});

			let button = frm.doc.disabled ? "Enable" : "Disable";

			frm.add_custom_button(__(button), function() {

				frm.set_value('disabled', 1 - frm.doc.disabled);

				frappe.call({
					method: "erpnext.accounts.doctype.accounting_dimension.accounting_dimension.disable_dimension",
					args: {
						doc: frm.doc
					},
					freeze: true,
					callback: function(r) {
						let message = frm.doc.disabled ? "Dimension Disabled" : "Dimension Enabled";
						frm.save();
						frappe.show_alert({message:__(message), indicator:'green'});
					}
				});
			});
		}
	},

	document_type: function(frm) {

		frm.set_value('label', frm.doc.document_type);
		frm.set_value('fieldname', frappe.model.scrub(frm.doc.document_type));

		frappe.db.get_value('Accounting Dimension', {'document_type': frm.doc.document_type}, 'document_type', (r) => {
			if (r && r.document_type) {
				frm.set_df_property('document_type', 'description', "Document type is already set as dimension");
			}
		});
	},
});

frappe.ui.form.on('Accounting Dimension Detail', {
	dimension_defaults_add: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.reference_document = frm.doc.document_type;
	}
});
