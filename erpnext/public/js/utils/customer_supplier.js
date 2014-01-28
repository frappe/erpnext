// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.provide("erpnext.utils");
erpnext.utils.get_party_details = function(frm, method, args) {
	if(!method) {
		if(frm.doc.customer) {
			method = "erpnext.selling.doctype.customer.customer.get_customer_details";
		} else {
			method = "erpnext.buying.doctype.supplier.supplier.get_supplier_details";
		}
	}
	if(!args) {
		if(frm.doc.customer) {
			args = { customer: frm.doc.customer };
		} else {
			args = { supplier: frm.doc.supplier };
		}
	}
	wn.call({
		method: method,
		args: args,
		callback: function(r) {
			if(r.message) {
				frm.updating_party_details = true;
				frm.set_value(r.message);
				frm.updating_party_details = false;
			}
		}
	});
}

erpnext.utils.get_address_display = function(frm, address_field) {
	if(frm.updating_party_details) return;
	if(!address_field) {
		if(frm.doc.customer) {
			address_field = "customer_address";
		} else {
			address_field = "supplier_address";
		}
	} 
	wn.call({
		method: "erpnext.utilities.doctype.address.address.get_address_display",
		args: {address: frm.doc[address_field] },
		callback: function(r) {
			if(r.message)
				frm.set_value("address_display", r.message)
		}
	})
}

erpnext.utils.get_contact_details = function(frm) {
	if(frm.updating_party_details) return;
	wn.call({
		method: "erpnext.utilities.doctype.contact.contact.get_contact_details",
		args: {address: frm.doc.contact_person },
		callback: function(r) {
			if(r.message)
				frm.set_value(r.message);
		}
	})
}