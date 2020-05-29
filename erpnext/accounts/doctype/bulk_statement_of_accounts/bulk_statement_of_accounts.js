// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Statement Of Accounts', {
	customer_collection: function(frm) {
			var collection_type = '';
			switch(frm.doc.customer_collection) {
				case 'Customer Group':
					// frm.set_query('customer', 'customers', function(frm){
					// 	console.log(frm.doc)
					// 	return {
					// 		filters: {
					// 			"customer": frm.doc.customer,
					// 			"customer_group": frm.doc.collection_name
					// 		}
					// 	}
					// });
				case 'Territory':
					frm.set_query('Bulk Statement Of Accounts Customers')
					break;
				case 'Sales Partner':
					frm.set_query('Bulk Statement Of Accounts Customers')
					break;
				case 'Sales Person':
					frm.set_query('Bulk Statement Of Accounts Customers')
					break;
			}
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