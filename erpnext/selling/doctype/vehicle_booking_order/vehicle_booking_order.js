// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.selling");

erpnext.selling.VehicleBookingOrder = frappe.ui.form.Controller.extend({
	setup: function () {

	},

	refresh: function () {
		erpnext.toggle_naming_series();
		erpnext.hide_company();
		this.set_customer_is_company_label();
		this.set_dynamic_link();
	},

	onload: function () {
		this.setup_queries();
	},

	setup_queries: function () {
		this.frm.set_query('contact_person', erpnext.queries.contact_query);
		this.frm.set_query('customer_address', erpnext.queries.address_query);
		this.frm.set_query("item_code", function() {
			return erpnext.queries.item({"is_vehicle": 1, "include_item_in_vehicle_booking": 1});
		});
		this.frm.set_query("payment_terms_template", function() {
			return {filters: {"include_in_vehicle_booking": 1}};
		});
	},

	company: function () {
		this.set_customer_is_company_label();
		if (this.frm.doc.company_is_customer) {
			this.get_customer_details();
		}
	},

	customer: function () {
		this.get_customer_details();
	},

	customer_is_company: function () {
		if (this.frm.doc.customer_is_company) {
			this.frm.doc.customer = "";
			this.frm.refresh_field('customer');
			this.frm.set_value("customer_name", this.frm.doc.company);
		} else {
			this.frm.set_value("customer_name", "");
		}

		this.get_customer_details();
		this.set_dynamic_link();
	},

	item_code: function () {
		var me = this;

		if (me.frm.doc.company && me.frm.doc.item_code) {
			me.frm.call({
				method: "erpnext.selling.doctype.vehicle_booking_order.vehicle_booking_order.get_item_details",
				child: me.frm.doc,
				args: {
					args: {
						company: me.frm.doc.company,
						item_code: me.frm.doc.item_code,
						customer: me.frm.doc.customer,
						supplier: me.frm.doc.supplier,
						tranasction_date: me.frm.doc.transaction_date,
						selling_tranction_type: me.frm.doc.selling_tranction_type,
						buying_tranction_type: me.frm.doc.buying_tranction_type,
						price_list: me.frm.doc.price_list
					}
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.trigger('vehicle_amount');
					}
				}
			});
		}
	},

	vehicle_amount: function () {
		this.calculate_taxes_and_totals();
	},

	fni_amount: function () {
		this.calculate_taxes_and_totals();
	},

	get_customer_details: function () {
		var me = this;

		if (me.frm.doc.company && (me.frm.doc.customer || me.frm.doc.company_is_customer)) {
			frappe.call({
				method: "erpnext.selling.doctype.vehicle_booking_order.vehicle_booking_order.get_customer_details",
				args: {
					args: {
						company: me.frm.doc.company,
						customer: me.frm.doc.customer,
						company_is_customer: me.frm.doc.company_is_customer
					}
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						me.frm.set_value(r.message);
					}
				}
			});
		}
	},

	set_customer_is_company_label: function() {
		if (this.frm.doc.company) {
			this.frm.fields_dict.customer_is_company.set_label(__("Customer is {0}", [this.frm.doc.company]));
		}
	},

	set_dynamic_link: function () {
		frappe.dynamic_link = {
			doc: this.frm.doc,
			fieldname: this.frm.doc.customer_is_company ? 'company' : 'customer',
			doctype: this.frm.doc.customer_is_company ? 'Company' : 'Customer'
		};
	},

	customer_address: function() {
		erpnext.utils.get_address_display(this.frm, 'customer_address', 'address_display');
	},

	contact_person: function() {
		erpnext.utils.get_contact_details(this.frm);
	},

	calculate_taxes_and_totals: function () {
		frappe.model.round_floats_in(this.frm.doc, ['vehicle_amount', 'fni_amount']);

		this.frm.doc.invoice_total = flt(this.frm.doc.vehicle_amount + this.frm.doc.fni_amount,
			precision('invoice_total'));

		this.frm.doc.customer_outstanding = this.frm.doc.invoice_total - flt(this.frm.doc.customer_advance);
		this.frm.doc.supplier_outstanding = this.frm.doc.invoice_total - flt(this.frm.doc.supplier_advance);

		this.frm.refresh_fields();
	},

	transaction_date: function () {
		this.frm.trigger('payment_terms_template');
	},

	delivery_date: function () {
		this.frm.trigger('payment_terms_template');
	},

	payment_terms_template: function() {
		var me = this;
		const doc = this.frm.doc;
		if(doc.payment_terms_template) {
			frappe.call({
				method: "erpnext.controllers.accounts_controller.get_payment_terms",
				args: {
					terms_template: doc.payment_terms_template,
					posting_date: doc.transaction_date,
					delivery_date: doc.delivery_date,
					grand_total: doc.invoice_total,
				},
				callback: function(r) {
					if(r.message && !r.exc) {
						me.frm.set_value("payment_schedule", r.message);
					}
				}
			})
		}
	},

	payment_term: function(doc, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.payment_term) {
			frappe.call({
				method: "erpnext.controllers.accounts_controller.get_payment_term_details",
				args: {
					term: row.payment_term,
					posting_date: this.frm.doc.transaction_date,
					delivery_date: this.frm.doc.delivery_date,
					grand_total: this.frm.doc.invoice_total
				},
				callback: function(r) {
					if(r.message && !r.exc) {
						for (var d in r.message) {
							frappe.model.set_value(cdt, cdn, d, r.message[d]);
						}
					}
				}
			})
		}
	},
});

$.extend(cur_frm.cscript, new erpnext.selling.VehicleBookingOrder({frm: cur_frm}));
