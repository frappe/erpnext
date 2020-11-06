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
		frm.add_custom_button(__('Customize Homepage Sections'), () => {
			frappe.set_route('List', 'Homepage Section', 'List');
		});
	},
});

frappe.ui.form.on('Homepage Featured Product', {

	view: function(frm, cdt, cdn){
		var child= locals[cdt][cdn]
		if(child.item_code && frm.doc.products_url){
			window.location.href = frm.doc.products_url + '/' + encodeURIComponent(child.item_code);
		}
	}
});
