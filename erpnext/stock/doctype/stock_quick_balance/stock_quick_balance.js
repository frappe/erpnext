// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Quick Balance', {

	setup: (frm) => {
		frm.set_query('item', () => {
			if (!frm.doc.warehouse) {
				frm.trigger('warehouse_check');
			}
		});
	},

	make_custom_button: (frm) => {
		if(frm.doc.item){
			frm.add_custom_button(__('Stock Balance Report'), () => {
				frappe.set_route('query-report', 'Stock Balance',
					{ 'item_code': frm.doc.item, 'warehouse': frm.doc.warehouse });
			}).addClass("btn-primary");
		}
	},

	refresh: (frm) => {
		frm.disable_save();
		frm.trigger('make_custom_button');
	},

	warehouse_check: (frm) => {
		frappe.msgprint(__('Please enter a Warehouse first'));
		frm.set_value('item', '');
	},

	warehouse: (frm) => {
		if (frm.doc.warehouse && frm.doc.item) {
			frm.trigger('item');
		}
	},

	date: (frm) => {
		if (frm.doc.warehouse && frm.doc.item) {
			frm.trigger('item');
		}
	},

	item: (frm) => {
		if (frm.doc.item) {
			frappe.call({
				method: 'erpnext.stock.doctype.stock_quick_balance.stock_quick_balance.get_item_stock_details',
				args: {
					'item': frm.doc.item,
					'warehouse': frm.doc.warehouse,
					'date': frm.doc.date
				},
				callback: (r) => {
					if (r.message) {
						let fields = ['image', 'qty', 'value'];

						if (r.message['item_barcode'].includes(frm.doc.item_barcode)) {
							fields.forEach(function (field) {
								frm.set_value(field, r.message[field]);
							});
							frm.set_value('image_view', r.message['image']);
						}

						else {
							fields.forEach(function (field) {
								frm.set_value(field, r.message[field]);
							});
							frm.set_value('item_barcode', r.message['item_barcode'][0]);
							frm.set_value('image_view', r.message['image']);
						}

					}
				}
			});
			frm.trigger('make_custom_button');
		}
	},

	item_barcode: (frm) => {
		if (!frm.doc.warehouse) {
			frm.trigger('warehouse_check');
		}

		else if (frm.doc.item_barcode) {
			frappe.call({
				method: 'erpnext.stock.doctype.stock_quick_balance.stock_quick_balance.get_barcode_stock_details',
				args: {
					'barcode': frm.doc.item_barcode,
					'warehouse': frm.doc.warehouse,
					'date': frm.doc.date
				},
				callback: (r) => {
					if (r.message) {
						let fields = ['item', 'item_name', 'item_description'];
						fields.forEach(function (field) {
							frm.set_value(field, r.message[field]);
						});
					}
				}
			});
		}
	}
});
