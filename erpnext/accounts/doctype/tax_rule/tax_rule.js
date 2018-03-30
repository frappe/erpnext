// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.add_fetch("customer", "customer_group", "customer_group" );
cur_frm.add_fetch("supplier", "supplier_type", "supplier_type" );

frappe.ui.form.on("Tax Rule", "tax_type", function(frm) {
	frm.toggle_reqd("sales_tax_template", frm.doc.tax_type=="Sales");
	frm.toggle_reqd("purchase_tax_template", frm.doc.tax_type=="Purchase");
})

frappe.ui.form.on("Tax Rule", "onload", function(frm) {
	if(frm.doc.__islocal) {
		frm.set_value("use_for_shopping_cart", 1);
	}
})

frappe.ui.form.on("Tax Rule", "refresh", function(frm) {
	frappe.ui.form.trigger("Tax Rule", "tax_type");
})

frappe.ui.form.on("Tax Rule", "customer", function(frm) {
	if(frm.doc.customer) {
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
	}
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
