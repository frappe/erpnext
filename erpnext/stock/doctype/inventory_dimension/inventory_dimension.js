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

	map_with_existing_field(frm) {
		frm.trigger('render_traget_field');
	},

	render_traget_field(frm) {
		if (frm.doc.map_with_existing_field && !frm.doc.disabled) {
			frappe.call({
				method: 'erpnext.stock.doctype.inventory_dimension.inventory_dimension.get_source_fieldnames',
				args: {
					reference_document: frm.doc.reference_document,
					ignore_document: frm.doc.name
				},
				callback: function(r) {
					if (r.message && r.message.length) {
						frm.set_df_property('stock_ledger_dimension', 'options', r.message);
					} else {
						frm.set_value("map_with_existing_field", 0);
						frappe.msgprint(__('Inventory Dimensions not found'));
					}
				}
			});
		}
	}
});
