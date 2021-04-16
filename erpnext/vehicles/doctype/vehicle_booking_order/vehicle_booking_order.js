// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleBookingOrder = frappe.ui.form.Controller.extend({
	setup: function () {
		this.frm.custom_make_buttons = {
			'Vehicle Booking Payment': 'Customer Payment',
			'Vehicle Receipt': 'Receive Vehicle',
			'Vehicle Delivery': 'Deliver Vehicle',
			'Vehicle Invoice Receipt': 'Receive Invoice',
			'Vehicle Invoice Delivery': 'Deliver Invoice',
			'Vehicle Transfer Letter': 'Transfer Letter',
			'Purchase Order': 'Purchase Order',
		}
	},

	refresh: function () {
		erpnext.toggle_naming_series();
		erpnext.hide_company();
		this.set_customer_is_company_label();
		this.set_dynamic_link();
		this.set_finance_type_mandatory();
		this.setup_route_options();
		this.setup_notification();
		this.add_create_buttons();
		this.setup_dashboard();
	},

	onload: function () {
		this.setup_queries();
	},

	setup_queries: function () {
		var me = this;

		this.frm.set_query('warehouse', () => erpnext.queries.warehouse(me.frm.doc));

		this.frm.set_query('customer', erpnext.queries.customer);
		this.frm.set_query('contact_person', () => {
			frappe.dynamic_link = {
				doc: this.frm.doc,
				fieldname: me.frm.doc.customer_is_company ? 'company' : 'customer',
				doctype: me.frm.doc.customer_is_company ? 'Company' : 'Customer'
			};
			return erpnext.queries.contact_query(me.frm.doc);
		});
		this.frm.set_query('financer_contact_person', () => {
			frappe.dynamic_link = {
				doc: this.frm.doc,
				fieldname: 'financer',
				doctype: 'Customer'
			};
			return erpnext.queries.contact_query(me.frm.doc);
		});
		this.frm.set_query('customer_address', () => {
			me.set_dynamic_link();
			return erpnext.queries.address_query(me.frm.doc);
		});

		this.frm.set_query("item_code", function() {
			return erpnext.queries.item({"is_vehicle": 1, "include_in_vehicle_booking": 1});
		});

		this.frm.set_query("payment_terms_template", function() {
			return {filters: {"include_in_vehicle_booking": 1}};
		});

		this.frm.set_query("vehicle", () => me.vehicle_query());

		this.frm.set_query("selling_transaction_type", function() {
			return {filters: {"selling": 1}};
		});
		this.frm.set_query("buying_transaction_type", function() {
			return {filters: {"buying": 1}};
		});

		this.frm.set_query("allocation_period", function () {
			var filters = {
				item_code: me.frm.doc.item_code,
				supplier: me.frm.doc.supplier,
				vehicle_color: me.frm.doc.color_1
			}
			if (me.frm.doc.delivery_period) {
				filters['delivery_period'] = me.frm.doc.delivery_period;
			}
			return erpnext.queries.vehicle_allocation_period('allocation_period', filters);
		});
		this.frm.set_query("delivery_period", () => me.delivery_period_query());

		this.frm.set_query("vehicle_allocation", () => me.allocation_query());

		this.frm.set_query("color_1", () => me.color_query());
		this.frm.set_query("color_2", () => me.color_query());
		this.frm.set_query("color_3", () => me.color_query());

		this.frm.set_query("additional_item_code", "additional_items", function(doc) {
			var filters = {'include_in_vehicle_booking': 1, 'is_vehicle': 0};
			if (doc.item_code) {
				filters.applicable_to_item = doc.item_code;
			}
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: filters
			}
		});
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

	allocation_query: function(ignore_allocation_period, dialog) {
		var filters = {
			item_code: this.frm.doc.item_code,
			supplier: this.frm.doc.supplier,
			vehicle_color: this.frm.doc.color_1,
			is_booked: 0,
			docstatus: 1
		}
		if (!ignore_allocation_period && this.frm.doc.allocation_period) {
			filters['allocation_period'] = this.frm.doc.allocation_period;
		}

		if (dialog) {
			var delivery_period = dialog.get_value('delivery_period');
			if (delivery_period) {
				filters['delivery_period'] = dialog.get_value('delivery_period');
			}
		} else {
			if (this.frm.doc.delivery_period) {
				filters['delivery_period'] = this.frm.doc.delivery_period;
			}
		}

		return {
			query: "erpnext.controllers.queries.vehicle_allocation_query",
			filters: filters
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

	setup_route_options: function () {
		var vehicle_field = this.frm.get_docfield("vehicle");
		var allocation_field = this.frm.get_docfield("vehicle_allocation");
		
		vehicle_field.get_route_options_for_new_doc = () => this.vehicle_route_options();
		allocation_field.get_route_options_for_new_doc = () => this.allocation_route_options();
	},

	vehicle_route_options: function() {
		return {
			"item_code": this.frm.doc.item_code,
			"item_name": this.frm.doc.item_name,
			"color": this.frm.doc.color_1,
			"unregistered": 1
		}
	},

	allocation_route_options: function() {
		return {
			"company": this.frm.doc.company,
			"item_code": this.frm.doc.item_code,
			"item_name": this.frm.doc.item_name,
			"supplier": this.frm.doc.supplier,
			"allocation_period": this.frm.doc.allocation_period || this.frm.doc.delivery_period,
			"delivery_period": this.frm.doc.delivery_period
		}
	},

	add_create_buttons: function () {
		// Customer Payment Button (allowed on draft too)
		if (this.frm.doc.docstatus < 2) {
			if (flt(this.frm.doc.customer_outstanding) > 0) {
				this.frm.add_custom_button(__('Customer Payment'),
					() => this.make_payment_entry(this.frm.doc.customer_is_company ? 'Company' : 'Customer'), __('Payment'));
			}
		}

		if (this.frm.doc.docstatus === 1) {
			var unpaid = flt(this.frm.doc.customer_outstanding) > 0 || flt(this.frm.doc.supplier_outstanding) > 0;

			// Supplier Payment Button
			if (flt(this.frm.doc.supplier_outstanding) > 0) {
				this.frm.add_custom_button(__('Supplier Payment'), () => this.make_payment_entry('Supplier'), __('Payment'));
			}

			// Receive/Deliver Vehicle and Invoice
			if (this.frm.doc.vehicle) {
				if (this.frm.doc.delivery_status === "To Receive") {
					this.frm.add_custom_button(__('Receive Vehicle'), () => this.make_next_document('Vehicle Receipt'));
				} else if (this.frm.doc.delivery_status === "To Deliver") {
					this.frm.add_custom_button(__('Deliver Vehicle'), () => this.make_next_document('Vehicle Delivery'));
				} else if (this.frm.doc.delivery_status === "Delivered" && !this.frm.doc.transfer_customer) {
					this.frm.add_custom_button(__('Transfer Letter'), () => this.make_next_document('Vehicle Transfer Letter'));
				}

				if (this.frm.doc.invoice_status === "To Receive") {
					this.frm.add_custom_button(__('Receive Invoice'), () => this.make_next_document('Vehicle Invoice Receipt'));
				} else if (this.frm.doc.invoice_status === "To Deliver" && this.frm.doc.delivery_status === "Delivered") {
					this.frm.add_custom_button(__('Deliver Invoice'), () => this.make_next_document('Vehicle Invoice Delivery'));
				}
			}

			// Change / Select labels
			var select_vehicle_label = this.frm.doc.vehicle ? "Change Vehicle" : "Select Vehicle";
			var select_allocation_label = this.frm.doc.vehicle_allocation ? "Change Vehicle Allocation" : "Select Allocation";
			var select_delivery_period_label = this.frm.doc.delivery_period ? "Change Delivery Period" : "Select Delivery Period";

			// Change Buttons
			if (this.frm.doc.__onload && this.frm.doc.__onload.can_change) {
				if (this.frm.doc.__onload.can_change.customer_details) {
					this.frm.add_custom_button(__("Update Customer Details"), () => this.change_customer_details(),
						__("Change"));
				}

				if (this.frm.doc.__onload.can_change.allocation) {
					this.frm.add_custom_button(__(select_allocation_label), () => this.change_allocation(),
						this.frm.doc.vehicle_allocation ? __("Change") : null);
				}

				if (this.frm.doc.__onload.can_change.delivery_period) {
					this.frm.add_custom_button(__(select_delivery_period_label), () => this.change_delivery_period(),
						this.frm.doc.delivery_period ? __("Change") : null);
				}

				if (this.frm.doc.__onload.can_change.color) {
					this.frm.add_custom_button(__("Change Vehicle Color"), () => this.change_color(),
						__("Change"));
				}

				if (this.frm.doc.__onload.can_change.vehicle) {
					this.frm.add_custom_button(__(select_vehicle_label), () => this.change_vehicle(),
						this.frm.doc.vehicle ? __("Change") : null);
				}

				if (this.frm.doc.__onload.can_change.payment_adjustment) {
					this.frm.add_custom_button(__("Change Payment Adjustment"), () => this.change_payment_adjustment(),
						__("Change"));
				}

				if (this.frm.doc.__onload.can_change.item) {
					this.frm.add_custom_button(__("Change Vehicle Item (Variant)"), () => this.change_item(),
						__("Change"));
				}
			}

			if (this.frm.doc.vehicle_allocation_required && !this.frm.doc.vehicle_allocation) {
				this.frm.custom_buttons[__(select_allocation_label)] && this.frm.custom_buttons[__(select_allocation_label)].addClass('btn-primary');
			}

			if (unpaid) {
				this.frm.page.set_inner_btn_group_as_primary(__('Payment'));
			} else if (this.frm.doc.status === "To Assign Vehicle") {
				this.frm.custom_buttons[__(select_vehicle_label)] && this.frm.custom_buttons[__(select_vehicle_label)].addClass('btn-primary');
			} else if (this.frm.doc.status === "To Receive Vehicle") {
				this.frm.custom_buttons[__('Receive Vehicle')] && this.frm.custom_buttons[__('Receive Vehicle')].addClass('btn-primary');
			} else if (this.frm.doc.status === "To Receive Invoice") {
				this.frm.custom_buttons[__('Receive Invoice')] && this.frm.custom_buttons[__('Receive Invoice')].addClass('btn-primary');
			} else if (this.frm.doc.status === "To Deliver Vehicle") {
				this.frm.custom_buttons[__('Deliver Vehicle')] && this.frm.custom_buttons[__('Deliver Vehicle')].addClass('btn-primary');
			} else if (this.frm.doc.status === "To Deliver Invoice") {
				this.frm.custom_buttons[__('Deliver Invoice')] && this.frm.custom_buttons[__('Deliver Invoice')].addClass('btn-primary');
			}
		}
	},

	setup_dashboard: function () {
		var me = this;
		var company_currency = erpnext.get_currency(me.frm.doc.company);

		var customer_outstanding_color = me.frm.doc.customer_outstanding ? "orange" : "green";
		me.frm.dashboard.add_indicator(__('Customer Outstanding: {0}',
			[format_currency(me.frm.doc.customer_outstanding, company_currency)]), customer_outstanding_color);

		var supplier_outstanding_color;
		if (!me.frm.doc.supplier_outstanding) {
			supplier_outstanding_color = "green";
		} else if (me.frm.doc.supplier_outstanding == me.frm.doc.customer_outstanding) {
			supplier_outstanding_color = "blue";
		} else {
			supplier_outstanding_color = "orange";
		}
		me.frm.dashboard.add_indicator(__('Supplier Outstanding: {0}',
			[format_currency(me.frm.doc.supplier_outstanding, company_currency)]), supplier_outstanding_color);

		var delivery_status_color;
		if (me.frm.doc.delivery_status == "To Receive") {
			delivery_status_color = "blue";
		} else if (me.frm.doc.delivery_status == "To Deliver") {
			delivery_status_color = "orange";
		} else if (me.frm.doc.delivery_status == "Delivered") {
			delivery_status_color = "green";
		}
		me.frm.dashboard.add_indicator(__('Delivery Status: {0}', [me.frm.doc.delivery_status]),
			delivery_status_color);

		var invoice_status_color;
		if (me.frm.doc.invoice_status == "To Receive") {
			invoice_status_color = "blue";
		} else if (me.frm.doc.invoice_status == "To Deliver") {
			invoice_status_color = "orange";
		} else if (me.frm.doc.invoice_status == "Delivered") {
			invoice_status_color = "green";
		}
		me.frm.dashboard.add_indicator(__('Invoice Status: {0}', [me.frm.doc.invoice_status]),
			invoice_status_color);

		var notification_count = JSON.parse(me.frm.doc.notification_count || '{}');

		var booking_confirmation_count = notification_count['Booking Confirmation'] || {};
		var booking_confirmation_color = booking_confirmation_count.sms ? "green" : "yellow";
		var booking_confirmation_status = booking_confirmation_count.sms ? __("{0} SMS", [cint(booking_confirmation_count.sms)])
			: __("Not Sent");
		me.frm.dashboard.add_indicator(__('Booking Confirmation: {0}', [booking_confirmation_status]),
			booking_confirmation_color);

		var balance_payment_count = notification_count['Balance Payment Request'] || {};
		var balance_payment_color = balance_payment_count.sms ? "green" : "yellow";
		var balance_payment_status = balance_payment_count.sms ? __("{0} SMS", [cint(balance_payment_count.sms)])
			: __("Not Sent");
		me.frm.dashboard.add_indicator(__('Balance Payment Request: {0}', [balance_payment_status]),
			balance_payment_color);

		var ready_for_delivery_count = notification_count['Ready For Delivery'] || {};
		var ready_for_delivery_color = ready_for_delivery_count.sms ? "green" : this.frm.doc.delivery_status == "To Deliver" ? "yellow" : "blue";
		var ready_for_delivery_status = ready_for_delivery_count.sms ? __("{0} SMS", [cint(ready_for_delivery_count.sms)])
			: __("Not Sent");
		me.frm.dashboard.add_indicator(__('Ready For Delivery: {0}', [ready_for_delivery_status]),
			ready_for_delivery_color);

		var congratulations_count = notification_count['Congratulations'] || {};
		var congratulations_color = congratulations_count.sms ? "green" : this.frm.doc.delivery_status == "Delivered" ? "yellow" : "blue";
		var congratulations_status = congratulations_count.sms ? __("{0} SMS", [cint(congratulations_count.sms)])
			: __("Not Sent");
		me.frm.dashboard.add_indicator(__('Congratutions: {0}', [congratulations_status]),
			congratulations_color);
	},

	setup_notification: function() {
		var me = this;
		if(this.frm.doc.docstatus === 1) {
			var notification_count = JSON.parse(this.frm.doc.notification_count || '{}');

			if (this.frm.doc.delivery_status == "To Receive") {
				var booking_confirmation_count = notification_count['Booking Confirmation'] || {};
				let label = __("Booking Confirmation{0}", [booking_confirmation_count.sms ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Booking Confirmation'),
					__("Notify"));
			}

			if (this.frm.doc.customer_outstanding) {
				var balance_payment_count = notification_count['Balance Payment Request'] || {};
				let label = __("Balance Payment Request{0}", [balance_payment_count.sms ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Balance Payment Request'),
					__("Notify"));
			}

			if (this.frm.doc.delivery_status == "To Deliver") {
				var ready_for_delivery_count = notification_count['Ready For Delivery'] || {};
				let label = __("Ready For Delivery{0}", [ready_for_delivery_count.sms ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Ready For Delivery'),
					__("Notify"));
			}

			if (this.frm.doc.delivery_status == "Delivered") {
				var congratulations_count = notification_count['Congratulations'] || {};
				let label = __("Congratulations{0}", [congratulations_count.sms ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Congratulations'),
					__("Notify"));
			}

			this.frm.add_custom_button(__("Custom Message"), () => this.send_sms('Custom Message'),
				__("Notify"));
		}
	},

	send_sms: function(type) {
		var sms_man = new erpnext.SMSManager(this.frm.doc, {
			method: "erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order.send_sms",
			type: type
		});
	},

	company: function () {
		this.set_customer_is_company_label();
		if (this.frm.doc.customer_is_company) {
			this.get_customer_details();
		}
	},

	customer: function () {
		this.get_customer_details();
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

	set_finance_type_mandatory: function () {
		this.frm.set_df_property('finance_type', 'reqd', this.frm.doc.financer ? 1 : 0);
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
	},

	item_code: function () {
		var me = this;

		if (me.frm.doc.company && me.frm.doc.item_code) {
			me.frm.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order.get_item_details",
				child: me.frm.doc,
				args: {
					args: {
						company: me.frm.doc.company,
						item_code: me.frm.doc.item_code,
						customer: me.frm.doc.customer,
						supplier: me.frm.doc.supplier,
						tranasction_date: me.frm.doc.transaction_date,
						selling_transaction_type: me.frm.doc.selling_transaction_type,
						buying_transaction_type: me.frm.doc.buying_transaction_type,
						vehicle_price_list: me.frm.doc.vehicle_price_list
					}
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.set_value("vehicle_allocation", null);
						me.frm.trigger('vehicle_amount');
					}
				}
			});
		}
	},

	vehicle_allocation_required: function () {
		if (!this.frm.doc.vehicle_allocation_required) {
			this.frm.set_value("vehicle_allocation", null);
			this.frm.set_value("allocation_period", null);
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

	get_customer_details: function () {
		var me = this;

		if (me.frm.doc.company && (me.frm.doc.customer || me.frm.doc.customer_is_company)) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order.get_customer_details",
				args: {
					args: {
						company: me.frm.doc.company,
						customer: me.frm.doc.customer,
						customer_is_company: me.frm.doc.customer_is_company,
						financer: me.frm.doc.financer,
						finance_type: me.frm.doc.finance_type,
						item_code: me.frm.doc.item_code,
						transaction_date: me.frm.doc.transaction_date
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
		var fieldname;
		var doctype;
		if (this.frm.doc.financer && this.frm.doc.finance_type === "Leased") {
			fieldname = 'financer';
			doctype = 'Customer';
		} else if (this.frm.doc.customer_is_company) {
			fieldname = 'company';
			doctype = 'Company';
		} else {
			fieldname = 'customer';
			doctype = 'Customer';
		}
		frappe.dynamic_link = {
			doc: this.frm.doc,
			fieldname: fieldname,
			doctype: doctype
		};
	},

	customer_address: function() {
		var me = this;

		frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order.get_address_details",
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
			method: "erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order.get_customer_contact_details",
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

	allocated_percentage: function () {
		this.calculate_taxes_and_totals();
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
		this.frm.trigger('payment_terms_template');
	},

	delivery_date: function () {
		if (this.frm.doc.delivery_date) {
			this.frm.set_value('due_date', this.frm.doc.delivery_date);
		}
	},

	due_date: function () {
		this.frm.trigger('payment_terms_template');
	},

	vehicle_allocation: function () {
		var me = this;
		if (me.frm.doc.vehicle_allocation) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_allocation.vehicle_allocation.get_allocation_details",
				args: {
					vehicle_allocation: this.frm.doc.vehicle_allocation,
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						$.each(['delivery_period', 'allocation_period'], function (i, fn) {
							if (r.message[fn]) {
								me.frm.doc[fn] = r.message[fn];
								me.frm.refresh_field(fn);
								delete r.message[fn];
							}
						});

						me.frm.set_value(r.message);
					}
				}
			});
		} else {
			me.frm.set_value("allocation_title", "");
		}
	},

	delivery_period: function () {
		var me = this;

		if (me.frm.doc.delivery_period) {
			me.frm.set_value("vehicle_allocation", null);

			frappe.db.get_value("Vehicle Allocation Period", me.frm.doc.delivery_period, "to_date", function (r) {
				if (r) {
					me.frm.set_value("delivery_date", r.to_date);
				}
			});
		}
	},

	allocation_period: function () {
		var me = this;

		if (me.frm.doc.allocation_period) {
			me.frm.set_value("vehicle_allocation", null);
		}
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

	tc_name: function() {
		var me = this;

		erpnext.utils.get_terms(this.frm.doc.tc_name, this.frm.doc, function(r) {
			if(!r.exc) {
				me.frm.set_value("terms", r.message);
			}
		});
	},

	make_payment_entry: function(party_type) {
		if (['Customer', 'Supplier', 'Company'].includes(party_type)) {
			return frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_payment.vehicle_booking_payment.get_payment_entry",
				args: {
					"vehicle_booking_order": this.frm.doc.name,
					"party_type": party_type,
				},
				callback: function (r) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			});
		}
	},

	make_next_document: function(doctype) {
		if (!doctype)
			return;

		return frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order.get_next_document",
			args: {
				"vehicle_booking_order": this.frm.doc.name,
				"doctype": doctype
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	},

	change_vehicle: function () {
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Select Vehicle"),
			fields: [
				{
					label: __("Vehicle"), fieldname: "vehicle", fieldtype: "Link", options: "Vehicle", reqd: 1,
					onchange: () => {
						let vehicle = dialog.get_value('vehicle');
						if (vehicle) {
							frappe.db.get_value("Vehicle", vehicle, ['color', 'chassis_no', 'engine_no'], (r) => {
								if (r) {
									dialog.set_values(r);
								}
							});
						}
					}, get_query: () => me.vehicle_query(), get_route_options_for_new_doc: () => me.vehicle_route_options()
				},
				{label: __("Chassis No"), fieldname: "chassis_no", fieldtype: "Data", read_only: 1},
				{label: __("Engine No"), fieldname: "engine_no", fieldtype: "Data", read_only: 1},
				{label: __("Color"), fieldname: "color", fieldtype: "Link", options: "Vehicle Color", read_only: 1},
			]
		});

		dialog.set_primary_action(__("Change"), function () {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_vehicle",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					vehicle: dialog.get_value('vehicle')
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		});
		dialog.show();
	},

	change_allocation: function () {
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Select Allocation"),
			fields: [
				{
					label: __("Vehicle Allocation"), fieldname: "vehicle_allocation", fieldtype: "Link", options: "Vehicle Allocation", reqd: 1,
					onchange: () => {
						let allocation = dialog.get_value('vehicle_allocation');
						if (allocation) {
							frappe.db.get_value("Vehicle Allocation", allocation, ['title', 'allocation_period', 'delivery_period'], (r) => {
								if (r) {
									dialog.set_values(r);
								}
							});
						}
					}, get_query: () => me.allocation_query(true, dialog), get_route_options_for_new_doc: () => me.allocation_route_options()
				},
				{label: __("Delivery Period"), fieldname: "delivery_period", fieldtype: "Link", options: "Vehicle Allocation Period",
					default: me.frm.doc.delivery_period, bold: 1, get_query: () => me.delivery_period_query(true)},
				{label: __("Allocation Code / Sr #"), fieldname: "title", fieldtype: "Data", read_only: 1},
				{label: __("Allocation Period"), fieldname: "allocation_period", fieldtype: "Link", options: "Vehicle Allocation Period", read_only: 1},
			]
		});

		dialog.set_primary_action(__("Change"), function () {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_allocation",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					vehicle_allocation: dialog.get_value('vehicle_allocation')
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		});
		dialog.show();
	},

	change_delivery_period: function () {
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Select Delivery Period"),
			fields: [
				{label: __("Delivery Period"), fieldname: "delivery_period", fieldtype: "Link", options: "Vehicle Allocation Period",
					reqd: 1, get_query: () => me.delivery_period_query(true)}
			]
		});

		dialog.set_primary_action(__("Change"), function () {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_delivery_period",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					delivery_period: dialog.get_value('delivery_period')
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		});
		dialog.show();
	},

	change_color: function () {
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Select Color"),
			fields: [
				{label: __("Color (1st Priority)"), fieldname: "color_1", fieldtype: "Link", options: "Vehicle Color", reqd: 1,
					get_query: () => me.color_query()},
				{label: __("Color (2nd Priority)"), fieldname: "color_2", fieldtype: "Link", options: "Vehicle Color",
					get_query: () => me.color_query()},
				{label: __("Color (3rd Priority)"), fieldname: "color_3", fieldtype: "Link", options: "Vehicle Color",
					get_query: () => me.color_query()},
			]
		});

		dialog.set_primary_action(__("Change"), function () {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_color",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					color_1: dialog.get_value('color_1'),
					color_2: dialog.get_value('color_2'),
					color_3: dialog.get_value('color_3'),
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		});
		dialog.show();
	},

	change_customer_details: function () {
		var me = this;

		frappe.confirm(__('Are you sure you want to update details from Customer Master(s)? This may change the Invoice Total.'),
			function() {
				frappe.call({
					method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_customer_details",
					args: {
						vehicle_booking_order: me.frm.doc.name,
					},
					callback: function (r) {
						if (!r.exc) {
							me.frm.reload_doc();
						}
					}
				});
			}
		)
	},

	change_item: function () {
		var me = this;

		frappe.db.get_value("Item", me.frm.doc.item_code, 'variant_of', (r) => {
			var variant_of = r.variant_of;
			var item_filters = {"is_vehicle": 1, "include_in_vehicle_booking": 1, "item_code": ['!=', me.frm.doc.item_code]}
			if (variant_of) {
				item_filters['variant_of'] = variant_of;
			}

			var dialog = new frappe.ui.Dialog({
				title: __("Change Vehicle Item (Variant)"),
				fields: [
					{
						label: __("Vehicle Item Code (Variant)"), fieldname: "item_code", fieldtype: "Link", options: "Item", reqd: 1,
						onchange: () => {
							let item_code = dialog.get_value('item_code');
							if (item_code) {
								frappe.db.get_value("Item", item_code, 'item_name', (r) => {
									if (r) {
										dialog.set_values(r);
									}
								});
							}
						},
						get_query: () => erpnext.queries.item(item_filters)
					},
					{label: __("Vehicle Item Name"), fieldname: "item_name", fieldtype: "Data", read_only: 1}
				]
			});

			dialog.set_primary_action(__("Change"), function () {
				frappe.call({
					method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_item",
					args: {
						vehicle_booking_order: me.frm.doc.name,
						item_code: dialog.get_value('item_code')
					},
					callback: function (r) {
						if (!r.exc) {
							me.frm.reload_doc();
							dialog.hide();
						}
					}
				});
			});
			dialog.show();
		});
	},

	change_payment_adjustment: function () {
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Change Payment Adjustment"),
			fields: [
				{label: __("Payment Adjustment Amount"), fieldname: "payment_adjustment", fieldtype: "Currency",
					options: "Comoany:company:default_currency", reqd: 1,
					description: __(frappe.meta.get_docfield("Vehicle Booking Order", "payment_adjustment").description)},
			]
		});

		dialog.set_primary_action(__("Change"), function () {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_payment_adjustment",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					payment_adjustment: dialog.get_value('payment_adjustment')
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		});
		dialog.show();
	},
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleBookingOrder({frm: cur_frm}));
