// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch("customer", "customer_group", "customer_group" );
cur_frm.add_fetch("supplier", "supplier_type", "supplier_type" );

cur_frm.toggle_reqd("sales_tax_template", cur_frm.doc.tax_type=="Sales");
cur_frm.toggle_reqd("purchase_tax_template", cur_frm.doc.tax_type=="Purchase");


frappe.ui.form.on("Tax Rule", "onload", function(frm) {
	if(frm.doc.__islocal){
		frm.set_value("use_for_shopping_cart", 1);
	}
})

frappe.ui.form.on("Tax Rule", "use_for_shopping_cart", function(frm) {
	if(!frm.doc.use_for_shopping_cart && (frappe.get_list("Tax Rule", {"use_for_shopping_cart":1}).length == 0)){
		frappe.model.get_value("Shopping Cart Settings", "Shopping Cart Settings", "enabled", function(docfield) {
			if(docfield.enabled){
				frm.set_value("use_for_shopping_cart", 1);
				frappe.throw(__("Shopping Cart is enabled"));
			}
		});
	}
})

frappe.ui.form.on("Tax Rule", "customer", function(frm) {
	frappe.call({
		method:"erpnext.accounts.doctype.tax_rule.tax_rule.get_party_details",
		args: {
			"party": frm.doc.customer,
			"party_type": "customer"
		},
		callback: function(r) {
			if(!r.exc) {
				$.each(r.message, function(k, v) {
					frm.set_value(k, v);
				});
			}
		}
	});
});

frappe.ui.form.on("Tax Rule", "supplier", function(frm) {
	frappe.call({
		method:"erpnext.accounts.doctype.tax_rule.tax_rule.get_party_details",
		args: {
			"party": frm.doc.supplier,
			"party_type": "supplier"
		},
		callback: function(r) {
			if(!r.exc) {
				$.each(r.message, function(k, v) {
					frm.set_value(k, v);
				});
			}
		}
	});
});