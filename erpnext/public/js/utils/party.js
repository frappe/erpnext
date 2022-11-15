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
	args.project = frm.doc.project;
	args.transaction_type = frm.doc.transaction_type;
	args.cost_center = frm.doc.cost_center;
	args.tax_id = frm.doc.tax_id;
	args.tax_cnic = frm.doc.tax_cnic;
	args.tax_strn = frm.doc.tax_strn;
	args.bill_to = frm.doc.bill_to;
	args.letter_of_credit = frm.doc.letter_of_credit;

	if (frappe.meta.has_field(frm.doc.doctype, 'has_stin')) {
		args["has_stin"] = cint(frm.doc.has_stin);
	}

	return frappe.call({
		method: method,
		args: args,
		callback: function(r) {
			if (r.message) {
				frm.supplier_tds = r.message.supplier_tds;
				frm.updating_party_details = true;
				return frappe.run_serially([
					() => frm.set_value(r.message),
					() => {
						frm.updating_party_details = false;
						if (callback) callback(r);
						frm.refresh_fields();
						erpnext.utils.add_item(frm);
					}
				]);
			}
		}
	});
}

erpnext.utils.get_party_account_details = function (frm) {
	if (!frm.doc.company) {
		return;
	}

	var party_type;
	var party;
	var account_field;
	if (frm.doc.letter_of_credit) {
		party_type = "Letter of Credit";
		party = frm.doc.letter_of_credit;
		account_field = "credit_to";
	} else if (frm.doc.supplier) {
		party_type = "Supplier";
		party = frm.doc.supplier;
		account_field = "credit_to";
	} else if (frm.doc.customer) {
		party_type = "Customer";
		party = frm.doc.bill_to || frm.doc.customer;
		account_field = "debit_to";
	} else {
		return;
	}

	frappe.call({
		method: "erpnext.accounts.party.get_party_account_details",
		args: {
			company: frm.doc.company,
			party_type: party_type,
			party: party,
			transaction_type: frm.doc.transaction_type
		},
		callback: function(r) {
			if(!r.exc && r.message) {
				frm.set_value(account_field, r.message.account);
				if (r.message.cost_center) {
					frm.set_value("cost_center", r.message.cost_center);
				}
			}
		}
	});
};

erpnext.utils.add_item = function(frm) {
	if (frm.is_new()) {
		var prev_route = frappe.get_prev_route();
		if (prev_route[0] === "Form" && prev_route[1]==='Item' && !(frm.doc.items && frm.doc.items.length)) {
			// add row
			var item = frm.add_child('items');
			frm.refresh_field('items');

			// set item
			frappe.model.set_value(item.doctype, item.name, 'item_code', prev_route.slice(2).join('/'));
		}
	}
}

erpnext.utils.get_address_display = function(frm, address_field, display_field, is_your_company_address) {
	if (frm.updating_party_details) return;

	var lead = erpnext.utils.get_lead_from_doc(frm);

	if (!address_field) {
		if (frm.doctype != "Purchase Order" && frm.doc.customer) {
			address_field = "customer_address";
		} else if (frm.doc.supplier) {
			address_field = "supplier_address";
		} else return;
	}

	if (!display_field) display_field = "address_display";

	frappe.call({
		method: "erpnext.accounts.party.get_address_display",
		args: {
			address: frm.doc[address_field] || "",
			lead: lead
		},
		callback: function(r) {
			if (!r.exc) {
				frm.set_value(display_field, r.message)
			}
		}
	})
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
	} else if (frm.doc.customer || frm.doc.bill_to) {
		party_type = 'Customer';
		party = frm.doc.bill_to || frm.doc.customer;
	} else if (frm.doc.supplier) {
		party_type = 'Supplier';
		party = frm.doc.supplier;
	} else if (frm.doc.quotation_to){
		party_type = frm.doc.quotation_to;
		party = frm.doc.party_name;
	}

	var args = {
		"party": party,
		"party_type": party_type,
		"posting_date": frm.doc.posting_date || frm.doc.transaction_date,
		"company": frm.doc.company,
		"customer_group": frm.doc.customer_group,
		"supplier_group": frm.doc.supplier_group,
		"tax_category": frm.doc.tax_category,
		"billing_address": ((frm.doc.customer || frm.doc.lead) ? (frm.doc.customer_address) : (frm.doc.supplier_address)),
		"shipping_address": frm.doc.shipping_address_name,
		"transaction_type": frm.doc.transaction_type,
		"cost_center": frm.doc.cost_center,
		"tax_id": frm.doc.tax_id,
		"tax_cnic": frm.doc.tax_cnic,
		"tax_strn": frm.doc.tax_strn
	};

	if (frappe.meta.has_field(frm.doc.doctype, 'has_stin')) {
		args["has_stin"] = cint(frm.doc.has_stin);
	}

	frappe.call({
		method: "erpnext.accounts.party.set_taxes",
		args: args,
		callback: function(r) {
			if (r.message){
				frm.set_value("taxes_and_charges", r.message)
			}
		}
	});
};

erpnext.utils.get_contact_details = function(frm) {
	if (frm.updating_party_details) return;

	var lead = erpnext.utils.get_lead_from_doc(frm);

	return frappe.call({
		method: "erpnext.accounts.party.get_contact_details",
		args: {
			contact: frm.doc.contact_person || "",
			project: frm.doc.project,
			lead: lead,
		},
		callback: function(r) {
			if (r.message) {
				return frm.set_value(r.message);
			}
		}
	});
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

erpnext.utils.get_shipping_address = function(frm, callback){
	if (frm.doc.company) {
		frappe.call({
			method: "frappe.contacts.doctype.address.address.get_shipping_address",
			args: {
				company: frm.doc.company,
				address: frm.doc.shipping_address
			},
			callback: function(r){
				if (r.message){
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

erpnext.utils.make_customer_from_lead = function (frm, lead) {
	if (!lead) {
		return;
	}

	frm.check_if_unsaved();

	var dialog = new frappe.ui.Dialog({
		title: __("Convert Lead to Customer"),
		fields: [
			{
				label: __("Lead"),
				fieldname: "lead",
				fieldtype: "Link",
				options: "Lead",
				read_only: 1,
				reqd: 1,
				default: lead,
			},
			{
				label: __("Existing Customer"),
				fieldname: "customer",
				fieldtype: "Link",
				options: "Customer",
				only_select: 1,
				description: __("Select Existing Customer to link or leave empty to create a new Customer"),
				get_query: () => erpnext.queries.customer(),
				onchange: () => {
					let customer = dialog.get_value('customer');
					if (customer) {
						frappe.db.get_value("Customer", customer, ['customer_name'], (r) => {
							if (r) {
								dialog.set_values(r);
							}
						});
					} else {
						dialog.set_value('customer_name', '');
					}
				}
			},
			{
				label: __("Existing Customer Name"),
				fieldname: "customer_name",
				fieldtype: "Data",
				read_only: 1,
				fetch_from: "customer.customer_name",
			},
		]
	});

	dialog.set_primary_action(__("Convert"), function () {
		var existing_customer = dialog.get_value('customer');
		if (existing_customer) {
			return frappe.call({
				method: "erpnext.crm.doctype.lead.lead.set_customer_for_lead",
				args: {
					lead: lead,
					customer: existing_customer,
				},
				callback: function (r) {
					if (!r.exc) {
						dialog.hide();

						if (frm.doc.doctype == "Lead") {
							frm.reload_doc();
						}
					}
				}
			})
		} else {
			dialog.hide();
			return frappe.model.open_mapped_doc({
				method: "erpnext.crm.doctype.lead.lead.make_customer",
				frm: frm,
				source_name: lead
			});
		}
	});

	dialog.show();
};

erpnext.utils.get_party_name = function (party_type, party, callback) {
	if (party_type && party) {
		return frappe.call({
			method: "erpnext.accounts.party.get_party_name",
			args: {
				party_type: party_type,
				party: party,
			},
			callback: function (r) {
				if (!r.exc) {
					callback && callback(r.message);
				}
			}
		});
	} else {
		callback && callback(null);
	}
};

erpnext.utils.get_party_name_field = function(party_type) {
	var dict = {'Customer': 'customer_name', 'Supplier': 'supplier_name', 'Employee': 'employee_name',
		'Member': 'member_name'};
	return dict[party_type] || "name";
};

erpnext.utils.get_lead_from_doc = function(frm) {
	if (frm.doc.party_name && [frm.doc.quotation_to, frm.doc.appointment_for, frm.doc.opportunity_from].includes("Lead")) {
		return frm.doc.party_name
	}
}
