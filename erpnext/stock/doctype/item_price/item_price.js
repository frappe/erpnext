// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Item Price", {
	onload: function (frm) {
		// Fetch price list details
		frm.add_fetch("price_list", "buying", "buying");
		frm.add_fetch("price_list", "selling", "selling");
		frm.add_fetch("price_list", "currency", "currency");

		// Fetch item details
		frm.add_fetch("item_code", "item_name", "item_name");
		frm.add_fetch("item_code", "description", "item_description");
		frm.add_fetch("item_code", "stock_uom", "uom");

		frm.set_df_property("bulk_import_help", "options",
			'<a href="#data-import-tool/Item Price">' + __("Import in Bulk") + '</a>');
	},
	item_code: function(frm) {
		if (frm.doc.item_code){
			frappe.call({
				method: 'frappe.client.get',
				args: {
					'doctype': 'Item',
					'name': frm.doc.item_code
				},
				callback: function(r){
					if (r && r.message.is_purchase_item && !r.message.is_sales_item) {
						frappe.call({
							method: 'frappe.client.get',
							args: {
								'doctype': 'Stock Settings',
								'name': 'Stock Settings'
							},
							callback: function(r){
								if (r && r.message.default_purchase_item_price_list){
									cur_frm.doc.price_list = r.message.default_purchase_item_price_list
									cur_frm.refresh_field('price_list')
								}
							}
						})
					} else if (r && !r.message.is_purchase_item && r.message.is_sales_item){
						frappe.call({
							method: 'frappe.client.get',
							args: {
								'doctype': 'Stock Settings',
								'name': 'Stock Settings'
							},
							callback: function(r){
								if (r && r.message.default_sales_item_price_list){
									cur_frm.doc.price_list = r.message.default_sales_item_price_list
									cur_frm.refresh_field('price_list')
								}
							}
						})

					} 
				}
			})
		}
	},
});
