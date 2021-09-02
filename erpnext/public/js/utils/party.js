// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.utils");

erpnext.utils.get_party_details = function(frm, method, args, callback) {
	if (!method) {
		method = "erpnext.accounts.party.get_party_details";
	}

	if (args) {
		if (in_list(['Sales Invoice', 'Sales Order', 'Delivery Note'], frm.doc.doctype)) {
			if (frm.doc.company_address && (!args.company_address)) {
				args.company_address = frm.doc.company_address;
			}
		}

		if (in_list(['Purchase Invoice', 'Purchase Order', 'Purchase Receipt'], frm.doc.doctype)) {
			if (frm.doc.shipping_address && (!args.shipping_address)) {
				args.shipping_address = frm.doc.shipping_address;
			}
		}
	}

	if (!args) {
		if ((frm.doctype != "Purchase Order" && frm.doc.customer)
			|| (frm.doc.party_name && in_list(['Quotation', 'Opportunity'], frm.doc.doctype))) {

			let party_type = "Customer";
			if (frm.doc.quotation_to && frm.doc.quotation_to === "Lead") {
				party_type = "Lead";
			}

			args = {
				party: frm.doc.customer || frm.doc.party_name,
				party_type: party_type,
				price_list: frm.doc.selling_price_list
			};
		} else if (frm.doc.supplier) {
			args = {
				party: frm.doc.supplier,
				party_type: "Supplier",
				bill_date: frm.doc.bill_date,
				price_list: frm.doc.buying_price_list
			};
		}

		if (in_list(['Sales Invoice', 'Sales Order', 'Delivery Note'], frm.doc.doctype)) {
			if (!args) {
				args = {
					party: frm.doc.customer || frm.doc.party_name,
					party_type: 'Customer'
				}
			}
			if (frm.doc.company_address && (!args.company_address)) {
				args.company_address = frm.doc.company_address;
			}

			if (frm.doc.shipping_address_name &&(!args.shipping_address_name)) {
				args.shipping_address_name = frm.doc.shipping_address_name;
			}
		}

		if (in_list(['Purchase Invoice', 'Purchase Order', 'Purchase Receipt'], frm.doc.doctype)) {
			if (!args) {
				args = {
					party: frm.doc.supplier,
					party_type: 'Supplier'
				}
			}

			if (frm.doc.shipping_address && (!args.shipping_address)) {
				args.shipping_address = frm.doc.shipping_address;
			}
		}

		if (args) {
			args.posting_date = frm.doc.posting_date || frm.doc.transaction_date;
			args.fetch_payment_terms_template = cint(!frm.doc.ignore_default_payment_terms_template);
		}
	}
	if (!args || !args.party) return;

	if (frappe.meta.get_docfield(frm.doc.doctype, "taxes")) {
		if (!erpnext.utils.validate_mandatory(frm, "Posting / Transaction Date",
			args.posting_date, args.party_type=="Customer" ? "customer": "supplier")) return;
	}

	if (!erpnext.utils.validate_mandatory(frm, "Company", frm.doc.company, args.party_type=="Customer" ? "customer": "supplier")) {
		return;
	}

	args.currency = frm.doc.currency;
	args.company = frm.doc.company;
	args.doctype = frm.doc.doctype;
	frappe.call({
		method: method,
		args: args,
		callback: function(r) {
			if (r.message) {
				frm.supplier_tds = r.message.supplier_tds;
				frm.updating_party_details = true;
				frappe.run_serially([
					() => frm.set_value(r.message),
					() => {
						frm.updating_party_details = false;
						if (callback) callback();
						frm.refresh();
						erpnext.utils.add_item(frm);
					}
				]);
			}
		}
	});
}

erpnext.utils.add_item = function(frm) {
	if (frm.is_new()) {
		var prev_route = frappe.get_prev_route();
		if (prev_route[1]==='Item' && !(frm.doc.items && frm.doc.items.length)) {
			// add row
			var item = frm.add_child('items');
			frm.refresh_field('items');

			// set item
			frappe.model.set_value(item.doctype, item.name, 'item_code', prev_route[2]);
		}
	}
}

erpnext.utils.get_address_display = function(frm, address_field, display_field, is_your_company_address) {
	if (frm.updating_party_details) return;

	if (!address_field) {
		if (frm.doctype != "Purchase Order" && frm.doc.customer) {
			address_field = "customer_address";
		} else if (frm.doc.supplier) {
			address_field = "supplier_address";
		} else return;
	}

	if (!display_field) display_field = "address_display";
	if (frm.doc[address_field]) {
		frappe.call({
			method: "frappe.contacts.doctype.address.address.get_address_display",
			args: {"address_dict": frm.doc[address_field] },
			callback: function(r) {
				if (r.message) {
					frm.set_value(display_field, r.message)
				}
			}
		})
	} else {
		frm.set_value(display_field, '');
	}
};

erpnext.utils.set_taxes_from_address = function(frm, triggered_from_field, billing_address_field, shipping_address_field) {
	if (frm.updating_party_details) return;

	if (frappe.meta.get_docfield(frm.doc.doctype, "taxes")) {
		if (!erpnext.utils.validate_mandatory(frm, "Lead / Customer / Supplier",
			frm.doc.customer || frm.doc.supplier || frm.doc.lead || frm.doc.party_name, triggered_from_field)) {
			return;
		}

		if (!erpnext.utils.validate_mandatory(frm, "Posting / Transaction Date",
			frm.doc.posting_date || frm.doc.transaction_date, triggered_from_field)) {
			return;
		}
	} else {
		return;
	}

	frappe.call({
		method: "erpnext.accounts.party.get_address_tax_category",
		args: {
			"tax_category": frm.doc.tax_category,
			"billing_address": frm.doc[billing_address_field],
			"shipping_address": frm.doc[shipping_address_field]
		},
		callback: function(r) {
			if (!r.exc){
				if (frm.doc.tax_category != r.message) {
					frm.set_value("tax_category", r.message);
				} else {
					erpnext.utils.set_taxes(frm, triggered_from_field);
				}
			}
		}
	});
};

erpnext.utils.set_taxes = function(frm, triggered_from_field) {
	if (frappe.meta.get_docfield(frm.doc.doctype, "taxes")) {
		if (!erpnext.utils.validate_mandatory(frm, "Company", frm.doc.company, triggered_from_field)) {
			return;
		}

		if (!erpnext.utils.validate_mandatory(frm, "Lead / Customer / Supplier",
			frm.doc.customer || frm.doc.supplier || frm.doc.lead || frm.doc.party_name, triggered_from_field)) {
			return;
		}

		if (!erpnext.utils.validate_mandatory(frm, "Posting / Transaction Date",
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
	} else if (frm.doc.quotation_to){
		party_type = frm.doc.quotation_to;
		party = frm.doc.party_name;
	}

	if (!frm.doc.company) {
		frappe.throw(__("Kindly select the company first"));
	}

	frappe.call({
		method: "erpnext.accounts.party.set_taxes",
		args: {
			"party": party,
			"party_type": party_type,
			"posting_date": frm.doc.posting_date || frm.doc.transaction_date,
			"company": frm.doc.company,
			"customer_group": frm.doc.customer_group,
			"supplier_group": frm.doc.supplier_group,
			"tax_category": frm.doc.tax_category,
			"billing_address": ((frm.doc.customer || frm.doc.lead) ? (frm.doc.customer_address) : (frm.doc.supplier_address)),
			"shipping_address": frm.doc.shipping_address_name
		},
		callback: function(r) {
			if (r.message){
				frm.set_value("taxes_and_charges", r.message)
			}
		}
	});
};

erpnext.utils.get_contact_details = function(frm) {
	if (frm.updating_party_details) return;

	if (frm.doc["contact_person"]) {
		frappe.call({
			method: "frappe.contacts.doctype.contact.contact.get_contact_details",
			args: {contact: frm.doc.contact_person },
			callback: function(r) {
				if (r.message)
					frm.set_value(r.message);
			}
		})
	}
}

erpnext.utils.validate_mandatory = function(frm, label, value, trigger_on) {
	if (!value) {
		frm.doc[trigger_on] = "";
		refresh_field(trigger_on);
		frappe.throw({message:__("Please enter {0} first", [label]), title:__("Mandatory")});
		return false;
	}
	return true;
}

erpnext.utils.get_shipping_address = function(frm, callback) {
	if (frm.doc.company) {
		if ((frm.doc.inter_company_order_reference || frm.doc.internal_invoice_reference ||
			frm.doc.internal_order_reference)) {
			if (callback) {
				return callback();
			}
		}
		frappe.call({
			method: "erpnext.accounts.custom.address.get_shipping_address",
			args: {
				company: frm.doc.company,
				address: frm.doc.shipping_address
			},
			callback: function(r) {
				if (r.message) {
					frm.set_value("shipping_address", r.message[0]) //Address title or name
					frm.set_value("shipping_address_display", r.message[1]) //Address to be displayed on the page
				}

				if (callback){
					return callback();
				}
			}
		});
	} else {
		frappe.msgprint(__("Select company first"));
	}
}
