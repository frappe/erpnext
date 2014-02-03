// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.provide("erpnext.utils");
erpnext.utils.get_party_details = function(frm, method, args) {
	if(!method) {
		method = "erpnext.accounts.party.get_party_details";
	}
	if(!args) {
		if(frm.doc.customer) {
			args = { 
				party: frm.doc.customer,
				party_type: "Customer",
				price_list: frm.doc.selling_price_list
			};
		} else {
			args = { 
				party: frm.doc.supplier,
				party_type: "Supplier",
				price_list: frm.doc.buying_price_list
			};
		}
	}
	args.currency = frm.doc.currency;
	args.company = frm.doc.company;
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
	if(frm.doc[address_field]) {
		wn.call({
			method: "erpnext.utilities.doctype.address.address.get_address_display",
			args: {address: frm.doc[address_field] },
			callback: function(r) {
				if(r.message)
					frm.set_value("address_display", r.message)
			}
		})
	}
}

erpnext.utils.get_contact_details = function(frm) {
	if(frm.updating_party_details) return;
	
	if(frm.doc[address_field]) {
		wn.call({
			method: "erpnext.utilities.doctype.contact.contact.get_contact_details",
			args: {contact: frm.doc.contact_person },
			callback: function(r) {
				if(r.message)
					frm.set_value(r.message);
			}
		})
	}
}