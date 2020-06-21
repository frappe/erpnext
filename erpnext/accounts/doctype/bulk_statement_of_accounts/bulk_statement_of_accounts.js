// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Statement Of Accounts', {
	customer_collection: function(frm){
		frm.doc.collection_name
		var collection_filter = [];
		switch(frm.doc.customer_collection) {
			case 'Territory':
				collection_filter = [
					['is_group', '=', 0]
				];
				break;
			case 'Sales Partner':
				break;
		}
		frm.set_query('collection_name', function(doc){
			return {
				filters: collection_filter
			}
		});
		frm.refresh();
	},
	collection_name: function(frm) {
		let child_filters = [];
		switch(frm.doc.customer_collection) {
			case 'Customer Group':
				child_filters = [
					['customer_group', '=', frm.doc.collection_name]
				];
				break;
			case 'Territory':
				child_filters = [
					['territory', '=', frm.doc.collection_name]
				];
				break;
			case 'Sales Partner':
				child_filters = [
					['default_sales_partner', '=', frm.doc.collection_name]
				];
				break;
		}
		frm.fields_dict['customer_list'].grid.get_field('customer').get_query = function(doc, cdt, cdn) {
			return {
				filters: child_filters
			}
		};
		cur_frm.fields_dict['customer_list'].frm.refresh();
	}
});


frappe.ui.form.on('Bulk Statement Of Accounts Customers', {
	setup: function(frm) {
		frm.set_query('customer', function(){
			return {
				company: frm.doc.customer,
				is_group: 0
			}
		});
	}
});