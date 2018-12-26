// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.utils");

erpnext.utils.get_party_details = function(frm, method, args, callback) {
	if(!method) {
		method = "erpnext.accounts.party.get_party_details";
	}
	if(!args) {
		if(frm.doctype != "Purchase Order" && frm.doc.customer) {
			args = {
				party: frm.doc.customer,
				party_type: "Customer",
				price_list: frm.doc.selling_price_list
			};
		} else if(frm.doc.supplier) {
			args = {
				party: frm.doc.supplier,
				party_type: "Supplier",
				bill_date: frm.doc.bill_date,
				price_list: frm.doc.buying_price_list
			};
		}

		if (args) {
			args.posting_date = frm.doc.posting_date || frm.doc.transaction_date;
		}
	}
	if(!args || !args.party) return;

	if(frappe.meta.get_docfield(frm.doc.doctype, "taxes")) {
		if(!erpnext.utils.validate_mandatory(frm, "Posting/Transaction Date",
			args.posting_date, args.party_type=="Customer" ? "customer": "supplier")) return;
	}

	args.currency = frm.doc.currency;
	args.company = frm.doc.company;
	args.doctype = frm.doc.doctype;
	frappe.call({
		method: method,
		args: args,
		callback: function(r) {
			if(r.message) {
				frm.supplier_tds = r.message.supplier_tds;
				frm.updating_party_details = true;
				frappe.run_serially([
					() => frm.set_value(r.message),
					() => {
						frm.updating_party_details = false;
						if(callback) callback();
						frm.refresh();
						erpnext.utils.add_item(frm);
					}
				]);
			}
		}
	});
}

erpnext.utils.add_item = function(frm) {
	if(frm.is_new()) {
		var prev_route = frappe.get_prev_route();
		if(prev_route[1]==='Item' && !(frm.doc.items && frm.doc.items.length)) {
			// add row
			var item = frm.add_child('items');
			frm.refresh_field('items');

			// set item
			frappe.model.set_value(item.doctype, item.name, 'item_code', prev_route[2]);
		}
	}
}

erpnext.utils.get_address_display = function(frm, address_field, display_field, is_your_company_address) {
	if(frm.updating_party_details) return;

	if(!address_field) {
		if(frm.doctype != "Purchase Order" && frm.doc.customer) {
			address_field = "customer_address";
		} else if(frm.doc.supplier) {
			address_field = "supplier_address";
		} else return;
	}

	if(!display_field) display_field = "address_display";
	if(frm.doc[address_field]) {
		frappe.call({
			method: "frappe.contacts.doctype.address.address.get_address_display",
			args: {"address_dict": frm.doc[address_field] },
			callback: function(r) {
				if(r.message) {
					frm.set_value(display_field, r.message)
				}
				if(frappe.meta.get_docfield(frm.doc.doctype, "taxes") && !is_your_company_address) {
					erpnext.utils.set_taxes(frm, address_field);
				}
			}
		})
	} else {
		frm.set_value(display_field, '');
	}
};

erpnext.utils.set_taxes = function(frm, triggered_from_field) {
	if(frappe.meta.get_docfield(frm.doc.doctype, "taxes")) {
		if(!erpnext.utils.validate_mandatory(frm, "Lead/Customer/Supplier",
			frm.doc.customer || frm.doc.supplier || frm.doc.lead, triggered_from_field)) {
			return;
		}

		if(!erpnext.utils.validate_mandatory(frm, "Posting/Transaction Date",
			frm.doc.posting_date || frm.doc.transaction_date, triggered_from_field)) {
			return;
		}
	} else {
		return;
	}

	var party_type, party;
	if (frm.doc.lead) {
		party_type = 'Lead';
		party = frm.doc.lead;
	} else if (frm.doc.customer) {
		party_type = 'Customer';
		party = frm.doc.customer;
	} else if (frm.doc.supplier) {
		party_type = 'Supplier';
		party = frm.doc.supplier;
	}

	frappe.call({
		method: "erpnext.accounts.party.set_taxes",
		args: {
			"party": party,
			"party_type": party_type,
			"posting_date": frm.doc.posting_date || frm.doc.transaction_date,
			"company": frm.doc.company,
			"tax_category": frm.doc.tax_category,
			"billing_address": ((frm.doc.customer || frm.doc.lead) ? (frm.doc.customer_address) : (frm.doc.supplier_address)),
			"shipping_address": frm.doc.shipping_address_name
		},
		callback: function(r) {
			if(r.message){
				frm.set_value("taxes_and_charges", r.message)
			}
		}
	});
};

erpnext.utils.get_contact_details = function(frm) {
	if(frm.updating_party_details) return;

	if(frm.doc["contact_person"]) {
		frappe.call({
			method: "frappe.contacts.doctype.contact.contact.get_contact_details",
			args: {contact: frm.doc.contact_person },
			callback: function(r) {
				if(r.message)
					frm.set_value(r.message);
			}
		})
	}
}

erpnext.utils.validate_mandatory = function(frm, label, value, trigger_on) {
	if(!value) {
		frm.doc[trigger_on] = "";
		refresh_field(trigger_on);
		frappe.msgprint(__("Please enter {0} first", [label]));
		return false;
	}
	return true;
}

erpnext.utils.get_shipping_address = function(frm, callback){
	if (frm.doc.company) {
		frappe.call({
			method: "frappe.contacts.doctype.address.address.get_shipping_address",
			args: {
				company: frm.doc.company,
				address: frm.doc.shipping_address
			},
			callback: function(r){
				if(r.message){
					frm.set_value("shipping_address", r.message[0]) //Address title or name
					frm.set_value("shipping_address_display", r.message[1]) //Address to be displayed on the page
				}

				if(callback){
					return callback();
				}
			}
		});
	} else {
		frappe.msgprint(__("Select company first"));
	}
}