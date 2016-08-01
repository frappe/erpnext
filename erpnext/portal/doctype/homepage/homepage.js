// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Homepage', {
	refresh: function(frm) {

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
	}
});
