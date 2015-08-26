// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.utils");
erpnext.utils.get_party_details = function(frm, method, args, callback) {
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
		} else if(frm.doc.supplier) {
			args = {
				party: frm.doc.supplier,
				party_type: "Supplier",
				price_list: frm.doc.buying_price_list
			};
		}
		args.posting_date = frm.doc.transaction_date;
	}
	if(!args) return;

	args.currency = frm.doc.currency;
	args.company = frm.doc.company;
	args.doctype = frm.doc.doctype;
	frappe.call({
		method: method,
		args: args,
		callback: function(r) {
			if(r.message) {
				frm.updating_party_details = true;
				frm.set_value(r.message);
				frm.updating_party_details = false;
				if(callback) callback();
			}
		}
	});
}

erpnext.utils.get_address_display = function(frm, address_field, display_field) {
	if(frm.updating_party_details) return;
	
	if(!address_field) {
		if(frm.doc.customer) {
			address_field = "customer_address";
		} else if(frm.doc.supplier) {
			address_field = "supplier_address";
		} else return;
	}
 
	if(!display_field) display_field = "address_display";
	if(frm.doc[address_field]) {
		frappe.call({
			method: "erpnext.utilities.doctype.address.address.get_address_display",
			args: {"address_dict": frm.doc[address_field] },
			callback: function(r) {
				if(r.message){
					frm.set_value(display_field, r.message)
				}
				frappe.call({
					method: "erpnext.accounts.party.set_taxes",
					args: {
						"party": frm.doc.customer || frm.doc.supplier,
						"party_type": (frm.doc.customer ? "Customer" : "Supplier"),
						"posting_date": frm.doc.posting_date || frm.doc.transaction_date,
						"company": frm.doc.company,
						"billing_address": ((frm.doc.customer) ? (frm.doc.customer_address) : (frm.doc.supplier_address)),
						"shipping_address": frm.doc.shipping_address_name
					},
					callback: function(r) {
						if(r.message){
							frm.set_value("taxes_and_charges", r.message)
						}
					}
				});
			}
		})
	}
}

erpnext.utils.get_contact_details = function(frm) {
	if(frm.updating_party_details) return;

	if(frm.doc["contact_person"]) {
		frappe.call({
			method: "erpnext.utilities.doctype.contact.contact.get_contact_details",
			args: {contact: frm.doc.contact_person },
			callback: function(r) {
				if(r.message)
					frm.set_value(r.message);
			}
		})
	}
}
