// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleRegistrationOrderController = erpnext.vehicles.VehicleAdditionalServiceController.extend({
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
			this.frm.doc.customer_outstanding = flt(this.frm.doc.customer_total);
			this.frm.doc.agent_outstanding = 0;
		}
	},
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleRegistrationOrderController({frm: cur_frm}));
