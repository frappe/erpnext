// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Homepage', {
	setup: function(frm) {
		frm.fields_dict["products"].grid.get_field("item_code").get_query = function(){
			return {
				filters: {'show_in_website': 1}
			}
		}
	},

	refresh: function(frm) {
		frm.add_custom_button(__('Set Meta Tags'), () => {
			frappe.utils.set_meta_tag('home');
		});
	},
});

frappe.ui.form.on('Homepage Featured Product', {
	item_code: function(frm, cdt, cdn) {
		var featured_product = frappe.model.get_doc(cdt, cdn);
		if (featured_product.item_code) {
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					'doctype': 'Item',
					'filters': {'name': featured_product.item_code},
					'fieldname': [
						'item_name',
						'web_long_description',
						'description',
						'image',
						'thumbnail'
					]
				},
				callback: function(r) {
					if (!r.exc) {
						$.extend(featured_product, r.message);
						if (r.message.web_long_description) {
							featured_product.description = r.message.web_long_description;
						}
						frm.refresh_field('products');
					}
				}
			});
		}
	},

	view: function(frm, cdt, cdn){
		var child= locals[cdt][cdn]
		if(child.item_code && frm.doc.products_url){
			window.location.href = frm.doc.products_url + '/' + encodeURIComponent(child.item_code);
		}
	}
});
