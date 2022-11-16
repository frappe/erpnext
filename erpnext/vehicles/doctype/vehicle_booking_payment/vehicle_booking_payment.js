// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleBookingPayment = class VehicleBookingPayment extends frappe.ui.form.Controller {
	setup() {
		this.frm.custom_make_buttons = {
			'Vehicle Booking Payment': 'Create Deposit',
		}
	}

	refresh() {
		erpnext.toggle_naming_series();
		erpnext.hide_company();
		this.set_instruments_table_read_only();
		this.add_create_buttons();
	}

	onload() {
		this.setup_queries();
	}

	setup_queries() {
		var me = this;

		this.frm.set_query('party_type', function () {
			var allowed_party_types = [];
			if (me.frm.doc.payment_type === "Receive") {
				allowed_party_types.push("Customer");
			} else if (me.frm.doc.payment_type === "Pay") {
				allowed_party_types.push("Supplier");
				allowed_party_types.push("Company");
			}

			return {
				filters: {
					name: ['in', allowed_party_types]
				}
			}
		});

		this.frm.set_query('vehicle_booking_order', function () {
			var filters = {
				docstatus: ['<', 2],
				status: ['!=', 'Cancelled Booking'],
				company: me.frm.doc.company,
			}

			if (me.frm.doc.party_type === "Customer") {
				filters['customer_outstanding'] = ['>', 0];
			}
			if (me.frm.doc.party_type === "Supplier") {
				filters['supplier_outstanding'] = ['>', 0];
			}

			return {
				filters: filters
			}
		});
	}

	add_create_buttons() {
		if (this.frm.doc.docstatus === 1 && this.frm.doc.payment_type === "Receive") {
			var undeposited = (this.frm.doc.instruments || []).filter(d => !cint(d.deposited));
			if (undeposited && undeposited.length) {
				var label = __("Create Deposit");
				this.frm.add_custom_button(label, () => this.make_deposit_entry());
				this.frm.custom_buttons[__(label)] && this.frm.custom_buttons[__(label)].addClass('btn-primary');
			}
		}
	}

	payment_type() {
		this.set_instruments_table_read_only();
		if (this.frm.doc.payment_type === "Receive") {
			this.frm.set_value("party_type", "Customer");
		} else if (this.frm.doc.payment_type === "Pay") {
			this.frm.set_value("party_type", "Supplier");
		}
	}

	party_type() {
		this.frm.set_value("party", "");
		this.get_vehicle_booking_party();
	}

	party() {
		var me = this;

		if (me.frm.doc.party_type && me.frm.doc.party) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_payment.vehicle_booking_payment.get_party_name",
				args: {
					party_type: me.frm.doc.party_type,
					party: me.frm.doc.party,
					vehicle_booking_order: me.frm.doc.vehicle_booking_order,
				},
				callback: function (r) {
					if (r.message) {
						me.frm.set_value('party_name', r.message);
					}
				}
			});
		}
	}

	vehicle_booking_order() {
		this.get_vehicle_booking_party();
		this.get_undeposited_instruments();
	}

	get_vehicle_booking_party() {
		var me = this;

		if (me.frm.doc.vehicle_booking_order && me.frm.doc.party_type) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_payment.vehicle_booking_payment.get_vehicle_booking_party",
				args: {
					vehicle_booking_order: me.frm.doc.vehicle_booking_order,
					party_type: me.frm.doc.party_type
				},
				callback: function (r) {
					if (r.message) {
						me.frm.set_value('party', r.message);
					}
				}
			});
		}
	}

	amount() {
		this.calculate_total_amount();
	}

	instruments_remove() {
		this.calculate_total_amount();
	}

	calculate_total_amount() {
		var me = this;

		me.frm.doc.total_amount = 0;
		$.each(me.frm.doc.instruments || [], function (i, d) {
			frappe.model.round_floats_in(d);
			me.frm.doc.total_amount += flt(d.amount);
		});

		me.frm.doc.total_amount = flt(me.frm.doc.total_amount, precision('total_amount'));
		me.frm.doc.in_words = "";
		me.frm.refresh_fields();
	}

	instruments_row_focused() {
		this.set_instruments_table_read_only();
	}

	set_instruments_table_read_only() {
		var editable = cint(this.frm.doc.payment_type !== "Pay");
		$.each(this.frm.get_field('instruments').grid.grid_rows || [], function (i, grid_row) {
			$.each(grid_row.docfields || [], function (i, df) {
				if (df.fieldname !== 'deposited') {
					grid_row.toggle_editable(df.fieldname, editable);
				}
			});
		});
	}

	get_undeposited_instruments() {
		var me = this;

		if (me.frm.doc.payment_type === "Pay" && me.frm.doc.vehicle_booking_order) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_payment.vehicle_booking_payment.get_undeposited_instruments",
				args: {
					reference_dt: 'Vehicle Booking Order',
					reference_dn: me.frm.doc.vehicle_booking_order,
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						me.frm.clear_table('instruments');

						$.each(r.message, function(i, d) {
							var ch = me.frm.add_child("instruments", d);
						});

						me.calculate_total_amount();
					}
				}
			});
		}
	}

	make_deposit_entry() {
		return frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_booking_payment.vehicle_booking_payment.get_deposit_entry",
			args: {
				"vehicle_booking_payment": this.frm.doc.name
			},
			callback: function (r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.vehicles.VehicleBookingPayment({frm: cur_frm}));
