frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleBookingController = frappe.ui.form.Controller.extend({
	refresh: function () {
		erpnext.toggle_naming_series();
		erpnext.hide_company();
		this.setup_route_options();
		this.set_finance_type_mandatory();
	},

	onload: function () {
		this.setup_queries();
	},

	setup_queries: function () {
		var me = this;

		if (this.frm.fields_dict.customer) {
			this.frm.set_query('customer', erpnext.queries.customer);
		}

		if (this.frm.fields_dict.financer) {
			this.frm.set_query('financer', erpnext.queries.customer);
		}

		if (this.frm.fields_dict.contact_person) {
			this.frm.set_query('contact_person', () => {
				me.set_customer_dynamic_link();
				return erpnext.queries.contact_query(me.frm.doc);
			});
		}

		if (this.frm.fields_dict.financer_contact_person) {
			this.frm.set_query('financer_contact_person', () => {
				me.set_financer_dynamic_link();
				return erpnext.queries.contact_query(me.frm.doc);
			});
		}

		if (this.frm.fields_dict.customer_address) {
			this.frm.set_query('customer_address', () => {
				me.set_dynamic_link();
				return erpnext.queries.address_query(me.frm.doc);
			});
		}

		if (this.frm.fields_dict.item_code) {
			this.frm.set_query("item_code", function () {
				return erpnext.queries.item({"is_vehicle": 1, "include_in_vehicle_booking": 1});
			});
		}

		if (this.frm.fields_dict.warehouse) {
			this.frm.set_query('warehouse', () => erpnext.queries.warehouse(me.frm.doc));
		}

		if (this.frm.fields_dict.payment_terms_template) {
			this.frm.set_query("payment_terms_template", function () {
				return {filters: {"include_in_vehicle_booking": 1}};
			});
		}

		if (this.frm.fields_dict.delivery_period) {
			this.frm.set_query("delivery_period", () => me.delivery_period_query());
		}

		if (this.frm.fields_dict.vehicle) {
			this.frm.set_query("vehicle", () => me.vehicle_query());
		}

		if (this.frm.fields_dict.color) {
			this.frm.set_query("color", () => me.color_query());
		}
		if (this.frm.fields_dict.color_1) {
			this.frm.set_query("color_1", () => me.color_query());
		}
		if (this.frm.fields_dict.color_2) {
			this.frm.set_query("color_2", () => me.color_query());
		}
		if (this.frm.fields_dict.color_3) {
			this.frm.set_query("color_3", () => me.color_query());
		}

		if (this.frm.fields_dict.additional_items) {
			this.frm.set_query("additional_item_code", "additional_items", function (doc) {
				var filters = {'include_in_vehicle_booking': 1, 'is_vehicle': 0};
				if (doc.item_code) {
					filters.applicable_to_item = doc.item_code;
				}
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: filters
				}
			});
		}
	},

	setup_route_options: function () {
		var vehicle_field = this.frm.get_docfield("vehicle");
		if (vehicle_field) {
			vehicle_field.get_route_options_for_new_doc = () => this.vehicle_route_options();
		}
	},

	vehicle_query: function () {
		return {
			filters: {
				item_code: this.frm.doc.item_code,
				delivery_document_no: ['is', 'not set'],
				is_booked: 0
			}
		};
	},

	delivery_period_query: function (ignore_allocation_period) {
		if (this.frm.doc.vehicle_allocation_required) {
			var filters = {
				item_code: this.frm.doc.item_code,
				supplier: this.frm.doc.supplier,
				vehicle_color: this.frm.doc.color_1
			}

			if (this.frm.doc.transaction_date) {
				filters['transaction_date'] = this.frm.doc.transaction_date;
			}
			if (!ignore_allocation_period && this.frm.doc.allocation_period) {
				filters['allocation_period'] = this.frm.doc.allocation_period;
			}
			return erpnext.queries.vehicle_allocation_period('delivery_period', filters);
		} else if (this.frm.doc.transaction_date) {
			return {
				filters: {to_date: [">=", this.frm.doc.transaction_date]}
			}
		}
	},

	color_query: function () {
		return erpnext.queries.vehicle_color({item_code: this.frm.doc.item_code});
	},

	vehicle_route_options: function() {
		return {
			"item_code": this.frm.doc.item_code,
			"item_name": this.frm.doc.item_name,
			"unregistered": 1
		}
	},

	set_customer_is_company_label: function() {
		if (this.frm.doc.company) {
			this.frm.fields_dict.customer_is_company.set_label(__("Customer is {0}", [this.frm.doc.company]));
		}
	},

	set_finance_type_mandatory: function () {
		if (this.frm.fields_dict.finance_type) {
			this.frm.set_df_property('finance_type', 'reqd', this.frm.doc.financer ? 1 : 0);
		}
	},

	set_dynamic_link: function (doc) {
		if (!doc) {
			doc = this.frm.doc;
		}

		if (doc.financer && doc.finance_type === "Leased") {
			this.set_financer_dynamic_link(doc);
		} else {
			this.set_customer_dynamic_link(doc);
		}
	},

	set_customer_dynamic_link: function (doc) {
		if (!doc) {
			doc = this.frm.doc;
		}

		var fieldname;
		var doctype;

		if (doc.customer_is_company) {
			fieldname = 'company';
			doctype = 'Company';
		} else if (doc.quotation_to) {
			fieldname = 'party_name';
			doctype = doc.quotation_to;
		} else {
			fieldname = 'customer';
			doctype = 'Customer';
		}

		frappe.dynamic_link = {
			doc: doc,
			fieldname: fieldname,
			doctype: doctype
		};
	},

	set_financer_dynamic_link: function (doc) {
		if (!doc) {
			doc = this.frm.doc;
		}

		frappe.dynamic_link = {
			doc: doc,
			fieldname: 'financer',
			doctype: 'Customer'
		};
	},

	financer: function () {
		this.set_finance_type_mandatory();

		if (this.frm.doc.finance_type) {
			this.get_customer_details();
		}

		if (!this.frm.doc.financer) {
			this.frm.set_value("finance_type", "");
		}
	},

	finance_type: function () {
		if (this.frm.doc.finance_type) {
			this.get_customer_details();
		}
	},

	get_customer_details: function () {
		var me = this;

		if (me.frm.doc.company && (me.frm.doc.customer || me.frm.doc.customer_is_company || (me.frm.doc.quotation_to && me.frm.doc.party_name))) {
			frappe.call({
				method: "erpnext.vehicles.vehicle_booking_controller.get_customer_details",
				args: {
					args: {
						doctype: me.frm.doc.doctype,
						company: me.frm.doc.company,
						customer: me.frm.doc.customer,
						customer_is_company: me.frm.doc.customer_is_company,
						quotation_to: me.frm.doc.quotation_to,
						party_name: me.frm.doc.party_name,
						financer: me.frm.doc.financer,
						finance_type: me.frm.doc.finance_type,
						transaction_date: me.frm.doc.transaction_date,
						item_code: me.frm.doc.item_code,
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

	get_item_details: function (callback) {
		var me = this;

		if (me.frm.doc.company && me.frm.doc.item_code) {
			me.frm.call({
				method: "erpnext.vehicles.vehicle_booking_controller.get_item_details",
				child: me.frm.doc,
				args: {
					args: {
						doctype: me.frm.doc.doctype,
						company: me.frm.doc.company,
						item_code: me.frm.doc.item_code,
						transaction_date: me.frm.doc.transaction_date,
						vehicle_price_list: me.frm.doc.vehicle_price_list,
						supplier: me.frm.doc.supplier,
						customer: me.frm.doc.customer,
						quotation_to: me.frm.doc.quotation_to,
						party_name: me.frm.doc.party_name,
						financer: me.frm.doc.financer,
						finance_type: me.frm.doc.finance_type,
					}
				},
				callback: function (r) {
					if (!r.exc) {
						frappe.run_serially([
							() => me.frm.trigger('vehicle_amount'),
							() => me.frm.trigger('payment_terms_template'),
							() => me.frm.trigger('image'),
							() => callback && callback(r)
						]);
					}
				}
			});
		}
	},

	item_code: function () {
		this.get_item_details();
	},

	delivery_period: function () {
		var me = this;

		if (me.frm.doc.delivery_period) {
			frappe.db.get_value("Vehicle Allocation Period", me.frm.doc.delivery_period, "to_date", function (r) {
				if (r) {
					me.frm.set_value("delivery_date", r.to_date);
				}
			});
		}
	},

	vehicle_amount: function () {
		this.calculate_taxes_and_totals();
	},

	withholding_tax_amount: function () {
		this.calculate_taxes_and_totals();
	},

	fni_amount: function () {
		this.calculate_taxes_and_totals();
	},

	allocated_percentage: function () {
		this.calculate_taxes_and_totals();
	},

	calculate_taxes_and_totals: function () {
		frappe.model.round_floats_in(this.frm.doc, ['vehicle_amount', 'fni_amount', 'withholding_tax_amount']);

		this.frm.doc.invoice_total = flt(this.frm.doc.vehicle_amount + this.frm.doc.fni_amount + this.frm.doc.withholding_tax_amount,
			precision('invoice_total'));

		if (this.frm.doc.docstatus === 0) {
			this.frm.doc.customer_advance = 0;
			this.frm.doc.supplier_advance = 0;
			this.frm.doc.customer_outstanding = this.frm.doc.invoice_total;
			this.frm.doc.supplier_outstanding = this.frm.doc.invoice_total;
		}

		this.calculate_contribution();

		this.frm.doc.in_words = "";

		this.frm.refresh_fields();
	},

	calculate_contribution: function() {
		var me = this;
		$.each(this.frm.doc.sales_team || [], function(i, sales_person) {
			frappe.model.round_floats_in(sales_person);
			if(sales_person.allocated_percentage) {
				sales_person.allocated_amount = flt(
					me.frm.doc.invoice_total * sales_person.allocated_percentage / 100.0,
					precision("allocated_amount", sales_person));
			}
		});
	},

	transaction_date: function () {
		this.get_vehicle_price();
		this.frm.trigger('payment_terms_template');
	},

	delivery_date: function () {
		if (this.frm.doc.delivery_date) {
			this.frm.trigger('payment_terms_template');
		}
	},

	customer_address: function() {
		var me = this;

		frappe.call({
			method: "erpnext.vehicles.vehicle_booking_controller.get_address_details",
			args: {
				address: cstr(this.frm.doc.customer_address),
			},
			callback: function (r) {
				if (r.message && !r.exc) {
					me.frm.set_value(r.message);
				}
			}
		});
	},

	contact_person: function() {
		this.get_contact_details();
	},

	financer_contact_person: function() {
		this.get_contact_details();
	},

	get_contact_details: function () {
		var me = this;

		frappe.call({
			method: "erpnext.vehicles.vehicle_booking_controller.get_customer_contact_details",
			args: {
				args: {
					customer: me.frm.doc.customer,
					financer: me.frm.doc.financer,
					finance_type: me.frm.doc.finance_type
				},
				customer_contact: me.frm.doc.contact_person,
				financer_contact: me.frm.doc.financer_contact_person
			},
			callback: function (r) {
				if (r.message && !r.exc) {
					me.frm.set_value(r.message);
				}
			}
		});
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
						if (me.frm.doc.payment_schedule && me.frm.doc.payment_schedule.length) {
							me.frm.set_value("due_date", me.frm.doc.payment_schedule[me.frm.doc.payment_schedule.length-1].due_date);
						} else {
							me.frm.set_value("due_date", doc.delivery_date);
						}
					}
				}
			})
		} else if(doc.delivery_date) {
			me.frm.set_value("payment_schedule", []);
			me.frm.set_value("due_date", doc.delivery_date);
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

	tc_name: function() {
		var me = this;

		erpnext.utils.get_terms(this.frm.doc.tc_name, this.frm.doc, function(r) {
			if(!r.exc) {
				me.frm.set_value("terms", r.message);
			}
		});
	},

	vehicle_price_list: function () {
		this.get_vehicle_price();
	},

	fni_price_list: function () {
		this.get_vehicle_price();
	},

	get_vehicle_price: function() {
		var me = this;

		if (me.frm.doc.company && me.frm.doc.item_code && me.frm.doc.vehicle_price_list) {
			me.frm.call({
				method: "erpnext.vehicles.vehicle_booking_controller.get_vehicle_price",
				child: me.frm.doc,
				args: {
					company: me.frm.doc.company,
					item_code: me.frm.doc.item_code,
					vehicle_price_list: me.frm.doc.vehicle_price_list,
					fni_price_list: me.frm.doc.fni_price_list,
					transaction_date: me.frm.doc.transaction_date,
					tax_status: me.frm.doc.tax_status,
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.trigger('vehicle_amount');
					}
				}
			});
		}
	},
});
