// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.provide("erpnext.utils");
erpnext.utils.get_customer_details = function(frm, method, args) {
	if(!method) 
		method = "erpnext.selling.doctype.customer.customer.get_customer_details";
	if(!args) 
		args = { customer: frm.doc.customer };
	wn.call({
		method: method,
		args: args,
		callback: function(r) {
			if(r.message) {
				frm.updating_customer_details = true;
				frm.set_value(r.message);
				frm.updating_customer_details = false;
			}
		}
	});
}

erpnext.utils.get_address_display = function(frm, address_field) {
	if(frm.updating_customer_details) return;
	if(!address_field) address_field = "customer_address";
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
	if(frm.updating_customer_details) return;
	wn.call({
		method: "erpnext.utilities.doctype.contact.contact.get_contact_details",
		args: {address: frm.doc.contact_person },
		callback: function(r) {
			if(r.message)
				frm.set_value(r.message);
		}
	})
}