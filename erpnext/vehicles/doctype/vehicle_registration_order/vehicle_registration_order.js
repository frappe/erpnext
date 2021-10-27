// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleRegistrationOrderController = erpnext.vehicles.VehicleAdditionalServiceController.extend({
	setup: function () {
		this._super();
		this.frm.custom_make_buttons = {
			'Vehicle Invoice Movement': 'Issue Invoice',
			'Vehicle Registration Receipt': 'Registration Receipt',
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
			filters['license_plate'] = ['is', 'not set'];

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

			if (this.frm.doc.vehicle) {
				// Invoice
				if (this.frm.doc.invoice_status == "In Hand" && !this.frm.doc.vehicle_license_plate) {
					this.frm.add_custom_button(__('Issue Invoice'), () => this.make_invoice_movement('Issue'));
				}
				else if (this.frm.doc.invoice_status == "Issued" && this.frm.doc.vehicle_license_plate) {
					this.frm.add_custom_button(__('Retrieve Invoice'), () => this.make_invoice_movement('Return'));
				}

				// Registration Receipt
				if (!this.frm.doc.vehicle_license_plate) {
					this.frm.add_custom_button(__('Registration Receipt'), () => this.make_registration_receipt());
				}
			}

			// Closing Entry
			var customer_margin = flt(flt(this.frm.doc.customer_total) - flt(this.frm.doc.authority_total),
				precision('customer_total'));
			var unclosed_customer_amount = flt(customer_margin - flt(this.frm.doc.customer_closed_amount),
				precision('customer_total'));
			var unclosed_agent_amount = flt(flt(this.frm.doc.agent_commission) - flt(this.frm.doc.agent_closed_amount),
				precision('agent_commission'));
			if (unclosed_customer_amount || (this.frm.doc.agent && unclosed_agent_amount)) {
				this.frm.add_custom_button(__('Closing Entry'), () => this.make_journal_entry('Closing Entry'));
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
			var filters = d => cint(d.is_choice_number);
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
			var filters = d => cint(d.is_ownership_transfer);
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

	calculate_totals: function () {
		erpnext.vehicles.pricing.calculate_total_price(this.frm, 'customer_charges', 'customer_total');
		erpnext.vehicles.pricing.calculate_total_price(this.frm, 'authority_charges', 'authority_total');

		frappe.model.round_floats_in(this.frm.doc, ['agent_commission']);

		this.frm.doc.margin_amount = flt(this.frm.doc.customer_total - this.frm.doc.authority_total
			- this.frm.doc.agent_commission, precision('margin_amount'));

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

			this.frm.doc.customer_outstanding = flt(this.frm.doc.customer_total) - flt(this.frm.doc.customer_payment);
			this.frm.doc.authority_outstanding = flt(this.frm.doc.authority_total) - flt(this.frm.doc.authority_payment);
		}
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
