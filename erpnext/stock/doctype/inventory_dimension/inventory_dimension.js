// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inventory Dimension', {
	setup(frm) {
		frm.trigger('set_query_on_fields');
	},

	set_query_on_fields(frm) {
		frm.set_query('reference_document', () => {
			let invalid_doctypes = frappe.model.core_doctypes_list;
			invalid_doctypes.push('Batch', 'Serial No', 'Warehouse', 'Item', 'Inventory Dimension',
				'Accounting Dimension', 'Accounting Dimension Filter');

			return {
				filters: {
					'istable': 0,
					'issingle': 0,
					'name': ['not in', invalid_doctypes]
				}
			};
		});

		frm.set_query('document_type', () => {
			return {
				query: 'erpnext.stock.doctype.inventory_dimension.inventory_dimension.get_inventory_documents',
			};
		});
	},

	onload(frm) {
		frm.trigger('render_traget_field');
	},

	refresh(frm) {
		if (frm.doc.__onload && frm.doc.__onload.has_stock_ledger
			&& frm.doc.__onload.has_stock_ledger.length) {
			let msg = __('Stock transactions exists against this dimension, user can not update document.');
			frm.dashboard.add_comment(msg, 'blue', true);

			frm.fields.forEach((field) => {
				if (field.df.fieldname !== 'disabled') {
					frm.set_df_property(field.df.fieldname, "read_only", "1");
				}
			});
		}
	}
});
