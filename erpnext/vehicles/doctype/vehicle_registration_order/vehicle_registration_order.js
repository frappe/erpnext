// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleRegistrationOrderController = class VehicleRegistrationOrderController extends erpnext.vehicles.VehicleAdditionalServiceController {
	setup() {
		super.setup();
		this.frm.custom_make_buttons = {
			'Vehicle Invoice Movement': 'Issue Invoice',
			'Vehicle Invoice Delivery': 'Deliver Invoice',
			'Vehicle Registration Receipt': 'Registration Receipt',
			'Vehicle Transfer Letter': 'Transfer Letter',
			'Sales Invoice': 'Create Invoice',
		}
	}

	refresh() {
		super.refresh();
		this.setup_buttons();
		this.frm.trigger('set_disallow_on_submit_fields_read_only');
	}

	setup_queries() {
		super.setup_queries();

		this.frm.set_query("vehicle_booking_order", function() {
			var filters = {
				registration_status: 'Not Ordered',
				status: ['!=', 'Cancelled Booking'],
				docstatus: 1,
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

		this.frm.set_query("component", "agent_charges",
			() => erpnext.vehicles.pricing.pricing_component_query('Registration'));
	}

	setup_route_options() {
		super.setup_route_options();

		var customer_component_field = this.frm.get_docfield("customer_charges", "component");
		customer_component_field.get_route_options_for_new_doc = () => {
			return erpnext.vehicles.pricing.pricing_component_route_options('Registration');
		}

		var authority_component_field = this.frm.get_docfield("authority_charges", "component");
		authority_component_field.get_route_options_for_new_doc = () => {
			return erpnext.vehicles.pricing.pricing_component_route_options('Registration');
		}

		var agent_component_field = this.frm.get_docfield("agent_charges", "component");
		agent_component_field.get_route_options_for_new_doc = () => {
			return erpnext.vehicles.pricing.pricing_component_route_options('Registration');
		}
	}

	setup_buttons() {
		if (this.frm.doc.docstatus == 1) {
			// Payment
			if (!cint(this.frm.doc.use_sales_invoice)) {
				this.frm.add_custom_button(__('Customer Payment'),
					() => this.make_journal_entry('Customer Payment'), __('Payment'));
			}
			if (flt(this.frm.doc.authority_outstanding)) {
				this.frm.add_custom_button(__('Authority Payment'),
					() => this.make_journal_entry('Authority Payment'), __('Payment'));
			}
			if (flt(this.frm.doc.agent_outstanding)) {
				this.frm.add_custom_button(__('Agent Payment'),
					() => this.make_journal_entry('Agent Payment'), __('Payment'));
			}

			//Sales Invoice
			var has_invoice = this.frm.doc.__onload && this.frm.doc.__onload.sales_invoice_exists;
			if (!has_invoice && cint(this.frm.doc.use_sales_invoice)) {
				this.frm.add_custom_button(__('Create Invoice'), () => this.make_sales_invoice());
			}

			// Closing Entry
			var unclosed_customer_amount = this.get_unclosed_customer_amount();
			var unclosed_agent_amount = this.get_unclosed_agent_amount();
			if (unclosed_customer_amount || unclosed_agent_amount) {
				this.frm.add_custom_button(__('Closing Entry'), () => this.make_journal_entry('Closing Entry'));
			}

			if (this.frm.doc.vehicle) {
				// Transfer Letter
				var transfer_letter_exists = this.frm.doc.__onload && this.frm.doc.__onload.transfer_letter_exists;
				if (this.frm.doc.ownership_transfer_required && !transfer_letter_exists) {
					this.frm.add_custom_button(__('Transfer Letter'), () => this.make_transfer_letter());
				}

				// Invoice
				if (this.frm.doc.invoice_status == "In Hand") {
					this.frm.add_custom_button(__('Issue Invoice'), () => this.make_invoice_movement('Issue'));
				}

				if (this.frm.doc.invoice_status == "Issued") {
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
			var unpaid = flt(this.frm.doc.customer_outstanding) > 0 || flt(this.frm.doc.authority_outstanding) > 0;

			if ((unpaid && !cint(this.frm.doc.use_sales_invoice)) || this.frm.doc.status == "To Pay Agent") {
				this.frm.page.set_inner_btn_group_as_primary(__('Payment'));
			} else if (this.frm.doc.status == "To Issue Invoice" && this.frm.doc.vehicle) {
				this.frm.custom_buttons[__('Issue Invoice')] && this.frm.custom_buttons[__('Issue Invoice')].addClass('btn-primary');
			} else if (this.frm.doc.status == "To Retrieve Invoice" && this.frm.doc.vehicle) {
				this.frm.custom_buttons[__('Retrieve Invoice')] && this.frm.custom_buttons[__('Retrieve Invoice')].addClass('btn-primary');
			} else if (this.frm.doc.status == "To Receive Receipt" && this.frm.doc.vehicle) {
				this.frm.custom_buttons[__('Registration Receipt')] && this.frm.custom_buttons[__('Registration Receipt')].addClass('btn-primary');
			} else if (this.frm.doc.status == "To Close Accounts") {
				this.frm.custom_buttons[__('Closing Entry')] && this.frm.custom_buttons[__('Closing Entry')].addClass('btn-primary');
			} else if (this.frm.doc.status == "To Bill") {
				this.frm.custom_buttons[__('Create Invoice')] && this.frm.custom_buttons[__('Create Invoice')].addClass('btn-primary');
			} else if (this.frm.doc.status == "To Deliver Invoice") {
				this.frm.custom_buttons[__('Deliver Invoice')] && this.frm.custom_buttons[__('Deliver Invoice')].addClass('btn-primary');
			}

		}
	}

	item_code() {
		var me = this;
		if (me.frm.doc.item_code) {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_selling_components: true,
				get_buying_components: true,
				get_agent_components: true,
				selling_components_field: 'customer_charges',
				buying_components_field: 'authority_charges',
				agent_components_field: 'agent_charges',
				clear_table: true,
				callback: function () {
					me.calculate_totals();
				}
			});
		}
	}

	component(doc, cdt, cdn) {
		var me = this;
		var row = frappe.get_doc(cdt, cdn);
		if (row.component) {
			var selling_or_buying;
			if (row.parentfield == 'customer_charges') {
				selling_or_buying = 'selling';
			} else if (row.parentfield == 'authority_charges') {
				selling_or_buying = 'buying';
			} else if (row.parentfield == 'agent_charges') {
				selling_or_buying = 'agent';
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
	}

	choice_number_required() {
		var me = this;
		if (cint(me.frm.doc.choice_number_required)) {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_selling_components: true,
				get_buying_components: true,
				get_agent_components: true,
				selling_components_field: 'customer_charges',
				buying_components_field: 'authority_charges',
				agent_components_field: 'agent_charges',
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
			erpnext.vehicles.pricing.remove_components(me.frm, 'agent_charges', filters);
		}
	}

	ownership_transfer_required() {
		var me = this;
		if (cint(me.frm.doc.ownership_transfer_required)) {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_selling_components: true,
				get_buying_components: true,
				get_agent_components: true,
				selling_components_field: 'customer_charges',
				buying_components_field: 'authority_charges',
				agent_components_field: 'agent_charges',
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
			erpnext.vehicles.pricing.remove_components(me.frm, 'agent_charges', filters);
		}
	}

	custom_license_plate_required() {
		var me = this;
		if (cint(me.frm.doc.custom_license_plate_required)) {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_selling_components: true,
				get_agent_components: true,
				selling_components_field: 'customer_charges',
				agent_components_field: 'agent_charges',
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
			erpnext.vehicles.pricing.remove_components(me.frm, 'agent_charges', filters);
		}
	}

	custom_license_plate_by_agent() {
		var me = this;

		if (!cint(me.frm.doc.custom_license_plate_required)) {
			return;
		}

		if (cint(me.frm.doc.custom_license_plate_by_agent)) {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_agent_components: true,
				agent_components_field: 'agent_charges',
				filters: {
					registration_component_type: 'License Plate'
				},
				callback: function () {
					me.calculate_totals();
				}
			});
		} else {
			var filters = d => cint(d.component_type == "License Plate");
			erpnext.vehicles.pricing.remove_components(me.frm, 'agent_charges', filters);
		}
	}

	tax_status() {
		var me = this;
		if (me.frm.doc.tax_status == "Non Filer") {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_selling_components: true,
				get_buying_components: true,
				get_agent_components: true,
				selling_components_field: 'customer_charges',
				buying_components_field: 'authority_charges',
				agent_components_field: 'agent_charges',
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
			erpnext.vehicles.pricing.remove_components(me.frm, 'agent_charges', filters);
		}
	}

	financer() {
		super.financer();

		var me = this;
		if (me.frm.doc.financer) {
			return erpnext.vehicles.pricing.get_pricing_components({
				frm: me.frm,
				component_type: "Registration",
				get_selling_components: true,
				get_buying_components: true,
				get_agent_components: true,
				selling_components_field: 'customer_charges',
				buying_components_field: 'authority_charges',
				agent_components_field: 'agent_charges',
				filters: {
					registration_component_type: 'HPA'
				},
				callback: function () {
					me.calculate_totals();
				}
			});
		} else {
			var filters = d => cint(d.component_type == "HPA");
			erpnext.vehicles.pricing.remove_components(me.frm, 'customer_charges', filters);
			erpnext.vehicles.pricing.remove_components(me.frm, 'authority_charges', filters);
			erpnext.vehicles.pricing.remove_components(me.frm, 'agent_charges', filters);
		}
	}

	component_amount() {
		this.calculate_totals();
	}

	customer_charges_remove() {
		this.calculate_totals();
	}

	authority_charges_remove() {
		this.calculate_totals();
	}

	instrument_amount() {
		this.calculate_totals();
	}

	customer_authority_instruments_remove() {
		this.calculate_totals();
	}

	sales_team_add() {
		this.calculate_sales_team_contribution();
	}
	allocated_percentage() {
		this.calculate_sales_team_contribution();
	}
	sales_person() {
		this.calculate_sales_team_contribution();
	}

	calculate_totals() {
		var me = this;

		erpnext.vehicles.pricing.calculate_total_price(me.frm, 'customer_charges', 'customer_total');
		erpnext.vehicles.pricing.calculate_total_price(me.frm, 'authority_charges', 'authority_total');
		erpnext.vehicles.pricing.calculate_total_price(me.frm, 'agent_charges', 'agent_total');

		me.frm.doc.margin_amount = flt(me.frm.doc.customer_total - me.frm.doc.authority_total - me.frm.doc.agent_total,
			precision('margin_amount'));

		me.frm.doc.customer_authority_payment = 0;
		$.each(me.frm.doc.customer_authority_instruments || [], function (i, d) {
			frappe.model.round_floats_in(d, ['instrument_amount']);
			me.frm.doc.customer_authority_payment += d.instrument_amount;
		});
		me.frm.doc.customer_authority_payment = flt(me.frm.doc.customer_authority_payment,
			precision('customer_authority_payment'));

		this.calculate_sales_team_contribution(true);
		this.reset_outstanding_amount();

		this.frm.refresh_fields();
	}

	calculate_sales_team_contribution(do_not_refresh) {
		erpnext.vehicles.pricing.calculate_sales_team_contribution(this.frm, this.frm.doc.customer_total);

		if (!do_not_refresh) {
			refresh_field('sales_team');
		}
	}

	reset_outstanding_amount() {
		if (this.frm.doc.docstatus === 0) {
			this.frm.doc.customer_payment = 0;
			this.frm.doc.customer_closed_amount = 0;

			this.frm.doc.authority_payment = 0;

			this.frm.doc.agent_payment = 0;
			this.frm.doc.agent_closed_amount = 0;
		}

		this.frm.doc.customer_outstanding = flt(this.frm.doc.customer_total) - flt(this.frm.doc.customer_payment) - flt(this.frm.doc.customer_authority_payment);
		this.frm.doc.authority_outstanding = flt(this.frm.doc.authority_total) - flt(this.frm.doc.authority_payment) - flt(this.frm.doc.customer_authority_payment);
		this.frm.doc.agent_outstanding = flt(this.frm.doc.agent_total) - flt(this.frm.doc.agent_payment);
	}

	get_unclosed_customer_amount() {
		var customer_margin = flt(flt(this.frm.doc.customer_total) - flt(this.frm.doc.authority_total),
			precision('customer_total'));
		return flt(customer_margin - flt(this.frm.doc.customer_closed_amount),
			precision('customer_total'));
	}

	get_unclosed_agent_amount() {
		return flt(flt(this.frm.doc.agent_total) - flt(this.frm.doc.agent_closed_amount),
			precision('agent_total'));
	}

	make_journal_entry(purpose) {
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
	}

	make_invoice_movement(purpose) {
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
	}

	make_invoice_delivery() {
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
	}

	make_transfer_letter() {
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
	}

	make_registration_receipt() {
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

	make_sales_invoice() {
		return frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order.make_sales_invoice",
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
};

extend_cscript(cur_frm.cscript, new erpnext.vehicles.VehicleRegistrationOrderController({frm: cur_frm}));
