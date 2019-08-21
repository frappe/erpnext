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
		frm.set_query('work_order', () => {
			return {
				query: 'erpnext.stock.doctype.pick_list.pick_list.get_pending_work_orders',
				filters: {
					'company': frm.doc.company
				}
			};
		});
	},
	refresh: (frm) => {
		frm.trigger('add_get_items_button');

		if (frm.doc.items && (frm.doc.items.length > 1 || frm.doc.items[0].item_code)) {
			frm.add_custom_button(__('Get Item Locations'), () => {
				frm.call('set_item_locations');
			}).addClass('btn-primary');
		}

		frm.add_custom_button(__('Delivery Note'), () => frm.trigger('make_delivery_note'), __('Create'));
	},
	work_order: (frm) => {
		frm.clear_table('items');
		erpnext.utils.map_current_doc({
			method: 'erpnext.manufacturing.doctype.work_order.work_order.create_pick_list',
			target: frm,
			source_name: frm.doc.work_order
		});
	},
	items_based_on: (frm) => {
		frm.trigger('add_get_items_button');
	},
	make_delivery_note(frm) {
		frappe.model.open_mapped_doc({
			method: 'erpnext.stock.doctype.pick_list.pick_list.make_delivery_note',
			frm: frm
		});
	},
	add_get_items_button(frm) {
		let source_doctype = frm.doc.items_based_on;
		if (source_doctype != 'Sales Order') return;
		let get_query_filters = {
			docstatus: 1,
			per_delivered: ['<', 100],
			status: ['!=', ''],
			customer: frm.doc.customer
		};
		frm.get_items_btn = frm.add_custom_button(__('Get Items'), () => {
			if (!frm.doc.customer) {
				frappe.msgprint(__('Please select Customer first'));
				return;
			}
			erpnext.utils.map_current_doc({
				method: 'erpnext.selling.doctype.sales_order.sales_order.make_pick_list',
				source_doctype: 'Sales Order',
				target: frm,
				setters: {
					company: frm.doc.company,
					customer: frm.doc.customer
				},
				date_field: 'transaction_date',
				get_query_filters: get_query_filters
			});
		});
	}
});
