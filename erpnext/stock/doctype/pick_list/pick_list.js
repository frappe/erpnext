// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pick List', {
	setup: (frm) => {
		frm.set_query('parent_warehouse', () => {
			return {
				filters: {
					'is_group': 1,
					'company': frm.doc.company
				}
			};
		});
	},
	refresh: (frm) => {
		frm.add_custom_button(__('Delivery Note'), () => frm.trigger('make_delivery_note'), __('Create'));
		frm.add_custom_button(__('Sales Order'), function() {
			erpnext.utils.map_current_doc({
				method: "erpnext.selling.doctype.sales_order.sales_order.make_pick_list",
				source_doctype: "Sales Order",
				target: frm,
				setters: {
					company: frm.doc.company || undefined,
				},
				get_query_filters: {
					docstatus: 1,
				}
			});
		}, __("Get items from"));

		if (frm.doc.reference_items && frm.doc.reference_items.length) {
			frm.add_custom_button(__('Get Item Locations'), () => {
				frm.call('set_item_locations');
			});
		}
	},
	make_delivery_note(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.pick_list.pick_list.make_delivery_note",
			frm: frm
		});
	},
});
