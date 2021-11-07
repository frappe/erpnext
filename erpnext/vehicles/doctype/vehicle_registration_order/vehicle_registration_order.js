// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleRegistrationOrderController = erpnext.vehicles.VehicleAdditionalServiceController.extend({
	setup: function () {
		this._super();
		this.frm.custom_make_buttons = {
			'Vehicle Invoice Movement': 'Issue Invoice',
			'Vehicle Invoice Delivery': 'Deliver Invoice',
			'Vehicle Registration Receipt': 'Registration Receipt',
			'Vehicle Transfer Letter': 'Transfer Letter',
		}
	},

	refresh: function () {
		this._super();
		this.setup_buttons();
		this.frm.trigger('set_fields_read_only');
	},

	set_fields_read_only: function (doc, cdt, cdn) {
		var me = this;

		if (!me.frm.doc.__onload || !me.frm.doc.__onload.disallow_on_submit || me.frm.doc.docstatus != 1) {
			return;
		}

		$.each(me.frm.doc.__onload.disallow_on_submit, function (i, d) {
			var fieldname = d[0];
			var parentfield = d[1];
			me.frm.set_df_property(fieldname, 'read_only', 1, parentfield ? cdn : null, parentfield);
		});
	},

	setup_queries: function () {
		this._super();

		var me = this;
		this.frm.set_query("vehicle", function () {
			var filters = {};

			if (me.frm.doc.item_code) {
				filters['item_code'] = me.frm.doc.item_code;
			}

			return {
				filters: filters
			}
		});

		this.frm.set_query("vehicle_booking_order", function() {
			var filters = {
				docstatus: 1,
				status: ['!=', 'Cancelled Booking'],
				registration_status: 'Not Ordered'
			}

			return {
				filters: filters
			};
		});

		this.frm.set_query('agent', erpnext.queries.supplier);

		this.frm.set_query("component", "customer_charges",
			() => erpnext.vehicles.pricing.pricing_component_query('Registration'));

		this.frm.set_query("component", "authority_charges",
			() => erpnext.vehicles.pricing.pricing_component_query('Registration'));
	},

	setup_route_options: function () {
		this._super();

		var customer_component_field = this.frm.get_docfield("customer_charges", "component");
		customer_component_field.get_route_options_for_new_doc = () => {
			return erpnext.vehicles.pricing.pricing_component_route_options('Registration');
		}

		var authority_component_field = this.frm.get_docfield("authority_charges", "component");
		authority_component_field.get_route_options_for_new_doc = () => {
			return erpnext.vehicles.pricing.pricing_component_route_options('Registration');
		}
	},

	setup_buttons: function () {
		if (this.frm.doc.docstatus == 1) {
			// Payment
			if (flt(this.frm.doc.customer_outstanding)) {
				this.frm.add_custom_button(__('Customer Payment'),
					() => this.make_journal_entry('Customer Payment'), __('Payment'));
			}
			if (flt(this.frm.doc.authority_outstanding)) {
				this.frm.add_custom_button(__('Authority Payment'),
					() => this.make_journal_entry('Authority Payment'), __('Payment'));
			}
			if (flt(this.frm.doc.agent_balance)) {
				this.frm.add_custom_button(__('Agent Payment'),
					() => this.make_journal_entry('Agent Payment'), __('Payment'));
			}

			// Closing Entry
			var customer_margin = flt(flt(this.frm.doc.customer_total) - flt(this.frm.doc.authority_total),
				precision('customer_total'));
			var unclosed_customer_amount = flt(customer_margin - flt(this.frm.doc.customer_closed_amount),
				precision('customer_total'));
			var unclosed_agent_amount = flt(flt(this.frm.doc.agent_total) - flt(this.frm.doc.agent_closed_amount),
				precision('agent_total'));
			if (unclosed_customer_amount || (this.frm.doc.agent && unclosed_agent_amount)) {
				this.frm.add_custom_button(__('Closing Entry'), () => this.make_journal_entry('Closing Entry'));
			}

			if (this.frm.doc.vehicle) {
				// Transfer Letter
				var transfer_letter_exists = this.frm.doc.__onload && this.frm.doc.__onload.transfer_letter_exists;
				if (this.frm.doc.ownership_transfer_required && !transfer_letter_exists) {
					this.frm.add_custom_button(__('Transfer Letter'), () => this.make_transfer_letter());
				}

				// Invoice
				if (this.frm.doc.invoice_status == "In Hand" && !this.frm.doc.vehicle_license_plate) {
					this.frm.add_custom_button(__('Issue Invoice'), () => this.make_invoice_movement('Issue'));
				} else if (this.frm.doc.invoice_status == "Issued") {
					this.frm.add_custom_button(__('Retrieve Invoice'), () => this.make_invoice_movement('Return'));
				} else if (this.frm.doc.invoice_status === "In Hand" && this.frm.doc.vehicle_license_plate) {
					this.frm.add_custom_button(__('Deliver Invoice'), () => this.make_invoice_delivery());
				}

				// Registration Receipt
				if (!this.frm.doc.vehicle_license_plate) {
					this.frm.add_custom_button(__('Registration Receipt'), () => this.make_registration_receipt());
				}
			}

			// Primary Button
			var unpaid = flt(this.frm.doc.customer_outstanding) > 0 || flt(this.frm.doc.authority_outstanding) > 0
				|| flt(this.frm.doc.agent_balance) > 0;

			if (unpaid) {
				this.frm.page.set_inner_btn_group_as_primary(__('Payment'));
			} else if (this.frm.doc.status == "To Issue Invoice" && this.frm.doc.vehicle) {
				this.frm.custom_buttons[__('Issue Invoice')] && this.frm.custom_buttons[__('Issue Invoice')].addClass('btn-primary');
			} else if (this.frm.doc.status == "To Retrieve Invoice" && this.frm.doc.vehicle) {
				this.frm.custom_buttons[__('Retrieve Invoice')] && this.frm.custom_buttons[__('Retrieve Invoice')].addClass('btn-primary');
			} else if (this.frm.doc.status == "To Receive Receipt" && this.frm.doc.vehicle) {
				this.frm.custom_buttons[__('Registration Receipt')] && this.frm.custom_buttons[__('Registration Receipt')].addClass('btn-primary');
			} else if (this.frm.doc.status == "To Close Accounts") {
				this.frm.custom_buttons[__('Closing Entry')] && this.frm.custom_buttons[__('Closing Entry')].addClass('btn-primary');
			} else if (this.frm.doc.status == "To Deliver Invoice") {
				this.frm.custom_buttons[__('Deliver Invoice')] && this.frm.custom_buttons[__('Deliver Invoice')].addClass('btn-primary');
			}

		}
	},

	item_code: function () {
		var me = this;
		if (me.frm.doc.item_code) {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_selling_components: true,
				get_buying_components: true,
				selling_components_field: 'customer_charges',
				buying_components_field: 'authority_charges',
				clear_table: true,
				callback: function () {
					me.calculate_totals();
				}
			});
		}
	},

	component: function (doc, cdt, cdn) {
		var me = this;
		var row = frappe.get_doc(cdt, cdn);
		if (row.component) {
			var selling_or_buying;
			if (row.parentfield == 'customer_charges') {
				selling_or_buying = 'selling';
			} else if (row.parentfield == 'authority_charges') {
				selling_or_buying = 'buying';
			}
			return erpnext.vehicles.pricing.get_component_details({
				frm: me.frm,
				row: row,
				component_name: row.component,
				selling_or_buying: selling_or_buying,
				callback: function () {
					me.calculate_totals();
				}
			});
		}
	},

	choice_number_required: function () {
		var me = this;
		if (cint(me.frm.doc.choice_number_required)) {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_selling_components: true,
				get_buying_components: true,
				selling_components_field: 'customer_charges',
				buying_components_field: 'authority_charges',
				filters: {
					registration_component_type: 'Choice Number'
				},
				callback: function () {
					me.calculate_totals();
				}
			});
		} else {
			var filters = d => cint(d.component_type == "Choice Number");
			erpnext.vehicles.pricing.remove_components(me.frm, 'customer_charges', filters);
			erpnext.vehicles.pricing.remove_components(me.frm, 'authority_charges', filters);
		}
	},

	ownership_transfer_required: function () {
		var me = this;
		if (cint(me.frm.doc.ownership_transfer_required)) {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_selling_components: true,
				get_buying_components: true,
				selling_components_field: 'customer_charges',
				buying_components_field: 'authority_charges',
				filters: {
					registration_component_type: 'Ownership Transfer'
				},
				callback: function () {
					me.calculate_totals();
				}
			});
		} else {
			var filters = d => cint(d.component_type == "Ownership Transfer");
			erpnext.vehicles.pricing.remove_components(me.frm, 'customer_charges', filters);
			erpnext.vehicles.pricing.remove_components(me.frm, 'authority_charges', filters);
		}
	},

	custom_license_plate_required: function () {
		var me = this;
		if (cint(me.frm.doc.custom_license_plate_required)) {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_selling_components: true,
				get_buying_components: true,
				selling_components_field: 'customer_charges',
				filters: {
					registration_component_type: 'License Plate'
				},
				callback: function () {
					me.calculate_totals();
				}
			});
		} else {
			var filters = d => cint(d.component_type == "License Plate");
			erpnext.vehicles.pricing.remove_components(me.frm, 'customer_charges', filters);
			erpnext.vehicles.pricing.remove_components(me.frm, 'authority_charges', filters);
			me.frm.set_value('agent_license_plate_charges', 0);
		}
	},

	custom_license_plate_by_agent: function () {
		var me = this;

		if (!cint(me.frm.doc.custom_license_plate_required)) {
			return;
		}

		if (cint(me.frm.doc.custom_license_plate_by_agent)) {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_buying_components: true,
				filters: {
					registration_component_type: 'License Plate'
				},
				callback: function () {
					me.calculate_totals();
				}
			});
		} else {
			me.frm.set_value('agent_license_plate_charges', 0);
		}
	},

	tax_status: function () {
		var me = this;
		if (me.frm.doc.tax_status == "Non Filer") {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_selling_components: true,
				get_buying_components: true,
				selling_components_field: 'customer_charges',
				buying_components_field: 'authority_charges',
				filters: {
					registration_component_type: 'Withholding Tax'
				},
				callback: function () {
					me.calculate_totals();
				}
			});
		} else {
			var filters = d => cint(d.component_type == "Withholding Tax");
			erpnext.vehicles.pricing.remove_components(me.frm, 'customer_charges', filters);
			erpnext.vehicles.pricing.remove_components(me.frm, 'authority_charges', filters);
		}
	},

	component_amount: function () {
		this.calculate_totals();
	},

	customer_charges_remove: function () {
		this.calculate_totals();
	},

	authority_charges_remove: function () {
		this.calculate_totals();
	},

	agent_commission: function () {
		this.calculate_totals();
	},

	agent_license_plate_charges: function () {
		this.calculate_totals();
	},

	instrument_amount: function () {
		this.calculate_totals();
	},

	customer_authority_instruments_remove: function () {
		this.calculate_totals();
	},

	calculate_totals: function () {
		var me = this;

		erpnext.vehicles.pricing.calculate_total_price(me.frm, 'customer_charges', 'customer_total');
		erpnext.vehicles.pricing.calculate_total_price(me.frm, 'authority_charges', 'authority_total');

		frappe.model.round_floats_in(me.frm.doc, ['agent_commission', 'agent_license_plate_charges']);
		me.frm.doc.agent_total = flt(me.frm.doc.agent_commission + me.frm.doc.agent_license_plate_charges,
			precision('agent_total'));

		me.frm.doc.margin_amount = flt(me.frm.doc.customer_total - me.frm.doc.authority_total
			- me.frm.doc.agent_total, precision('margin_amount'));

		me.frm.doc.customer_authority_payment = 0;
		$.each(me.frm.doc.customer_authority_instruments || [], function (i, d) {
			frappe.model.round_floats_in(d, ['instrument_amount']);
			me.frm.doc.customer_authority_payment += d.instrument_amount;
		});
		me.frm.doc.customer_authority_payment = flt(me.frm.doc.customer_authority_payment,
			precision('customer_authority_payment'));

		this.reset_outstanding_amount();

		this.frm.refresh_fields();
	},

	reset_outstanding_amount: function () {
		if (this.frm.doc.docstatus === 0) {
			this.frm.doc.customer_payment = 0;
			this.frm.doc.customer_closed_amount = 0;
			this.frm.doc.authority_payment = 0;
			this.frm.doc.agent_payment = 0;
			this.frm.doc.agent_balance = 0;
			this.frm.doc.agent_closed_amount = 0;
		}

		this.frm.doc.customer_outstanding = flt(this.frm.doc.customer_total) - flt(this.frm.doc.customer_payment) - flt(this.frm.doc.customer_authority_payment);
		this.frm.doc.authority_outstanding = flt(this.frm.doc.authority_total) - flt(this.frm.doc.authority_payment) - flt(this.frm.doc.customer_authority_payment);
	},

	make_journal_entry: function(purpose) {
		if (!purpose)
			return;

		return frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order.get_journal_entry",
			args: {
				"vehicle_registration_order": this.frm.doc.name,
				"purpose": purpose
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	},

	make_invoice_movement: function(purpose) {
		if (!purpose)
			return;

		return frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order.get_invoice_movement",
			args: {
				"vehicle_registration_order": this.frm.doc.name,
				"purpose": purpose
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	},

	make_invoice_delivery: function() {
		return frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order.get_invoice_delivery",
			args: {
				"vehicle_registration_order": this.frm.doc.name
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	},

	make_transfer_letter: function() {
		return frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order.get_transfer_letter",
			args: {
				"vehicle_registration_order": this.frm.doc.name
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	},

	make_registration_receipt: function () {
		return frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order.get_registration_receipt",
			args: {
				"vehicle_registration_order": this.frm.doc.name,
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleRegistrationOrderController({frm: cur_frm}));
