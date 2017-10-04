// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Restaurant Order Entry', {
	setup: function(frm) {
		let get_item_query = () => {
			return {
				query: 'erpnext.restaurant.doctype.restaurant_order_entry.restaurant_order_entry.item_query_restaurant',
				filters: {
					'table': frm.doc.restaurant_table
				}
			};
		};
		frm.set_query('item', 'items', get_item_query);
		frm.set_query('add_item', get_item_query);
	},
	onload_post_render: function(frm) {
		if(!this.item_selector) {
			this.item_selector = new erpnext.ItemSelector({
				frm: frm,
				item_field: 'item',
				item_query: 'erpnext.restaurant.doctype.restaurant_order_entry.restaurant_order_entry.item_query_restaurant',
				get_filters: () => {
					return {table: frm.doc.restaurant_table};
				}
			});
		}

		let $input = frm.get_field('add_item').$input;

		$input.on('keyup', function(e) {
			if (e.which===13) {
				if (frm.clear_item_timeout) {
					clearTimeout (frm.clear_item_timeout);
				}

				// clear the item input so user can enter a new item
				frm.clear_item_timeout = setTimeout (() => {
					frm.set_value('add_item', '');
				}, 1000);

				let item = $input.val();

				if (!item) return;

				var added = false;
				(frm.doc.items || []).forEach((d) => {
					if (d.item===item) {
						d.qty += 1;
						added = true;
					}
				});

				return frappe.run_serially([
					() => {
						if (!added) {
							return frm.add_child('items', {item: item, qty: 1});
						}
					},
					() => frm.get_field("items").refresh()
				]);
			}
		});
	},
	refresh: function(frm) {
		frm.disable_save();
		frm.add_custom_button(__('Update'), () => {
			return frm.trigger('sync');
		});
		frm.add_custom_button(__('Clear'), () => {
			return frm.trigger('clear');
		});
		frm.add_custom_button(__('Bill'), () => {
			return frm.trigger('make_invoice');
		});
	},
	clear: function(frm) {
		frm.doc.add_item = '';
		frm.doc.grand_total = 0;
		frm.doc.items = [];
		frm.refresh();
		frm.get_field('add_item').$input.focus();
	},
	restaurant_table: function(frm) {
		// select the open sales order items for this table
		if (!frm.doc.restaurant_table) {
			return;
		}
		return frappe.call({
			method: 'erpnext.restaurant.doctype.restaurant_order_entry.restaurant_order_entry.get_invoice',
			args: {
				table: frm.doc.restaurant_table
			},
			callback: (r) => {
				frm.events.set_invoice_items(frm, r);
			}
		});
	},
	sync: function(frm) {
		return frappe.call({
			method: 'erpnext.restaurant.doctype.restaurant_order_entry.restaurant_order_entry.sync',
			args: {
				table: frm.doc.restaurant_table,
				items: frm.doc.items
			},
			callback: (r) => {
				frm.events.set_invoice_items(frm, r);
				frappe.show_alert({message: __('Saved'), indicator: 'green'});
			}
		});

	},
	make_invoice: function(frm) {
		frm.trigger('sync').then(() => {
			frappe.prompt([
				{
					fieldname: 'customer',
					label: __('Customer'),
					fieldtype: 'Link',
					reqd: 1,
					options: 'Customer',
					'default': frm.invoice.customer
				},
				{
					fieldname: 'mode_of_payment',
					label: __('Mode of Payment'),
					fieldtype: 'Link',
					reqd: 1,
					options: 'Mode of Payment',
					'default': frm.mode_of_payment || ''
				}
			], (data) => {
				// cache this for next entry
				frm.mode_of_payment = data.mode_of_payment;
				return frappe.call({
					method: 'erpnext.restaurant.doctype.restaurant_order_entry.restaurant_order_entry.make_invoice',
					args: {
						table: frm.doc.restaurant_table,
						customer: data.customer,
						mode_of_payment: data.mode_of_payment
					},
					callback: (r) => {
						frm.set_value('last_sales_invoice', r.message);
						frm.trigger('clear');
					}
				});
			},
			__("Select Customer"));
		});
	},
	set_invoice_items: function(frm, r) {
		let invoice = r.message;
		frm.doc.items = [];
		(invoice.items || []).forEach((d) => {
			frm.add_child('items', {item: d.item_code, qty: d.qty, rate: d.rate});
		});
		frm.set_value('grand_total', invoice.grand_total);
		frm.set_value('last_sales_invoice', invoice.name);
		frm.invoice = invoice;
		frm.refresh();
	}
});
