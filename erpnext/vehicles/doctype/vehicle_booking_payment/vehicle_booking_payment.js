// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleBookingPayment = frappe.ui.form.Controller.extend({
	refresh: function() {
		erpnext.toggle_naming_series();
		erpnext.hide_company();
		this.set_instruments_table_read_only();
	},

	onload: function () {
		this.setup_queries();
	},

	setup_queries: function () {
		var me = this;

		this.frm.set_query('party_type', function () {
			var allowed_party_types = [];
			if (me.frm.doc.payment_type === "Receive") {
				allowed_party_types.push("Customer");
			} else if (me.frm.doc.payment_type === "Pay") {
				allowed_party_types.push("Supplier");
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
				company: me.frm.doc.company
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
	},

	payment_type: function () {
		this.set_instruments_table_read_only();
		if (this.frm.doc.payment_type === "Receive") {
			this.frm.set_value("party_type", "Customer");
		} else if (this.frm.doc.payment_type === "Pay") {
			this.frm.set_value("party_type", "Supplier");
		}
	},

	party_type: function () {
		this.frm.set_value("party", "");
		this.get_vehicle_booking_party();
	},

	party: function () {
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
	},

	vehicle_booking_order: function () {
		this.get_vehicle_booking_party();
		this.get_undeposited_instruments();
	},

	get_vehicle_booking_party: function () {
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
	},

	amount: function () {
		this.calculate_total_amount();
	},

	instruments_remove: function () {
		this.calculate_total_amount();
	},

	calculate_total_amount: function () {
		var me = this;

		me.frm.doc.total_amount = 0;
		$.each(me.frm.doc.instruments || [], function (i, d) {
			frappe.model.round_floats_in(d);
			me.frm.doc.total_amount += flt(d.amount);
		});

		me.frm.doc.total_amount = flt(me.frm.doc.total_amount, precision('total_amount'));
		me.frm.doc.in_words = "";
		me.frm.refresh_fields();
	},

	instruments_row_focused: function () {
		this.set_instruments_table_read_only();
	},

	set_instruments_table_read_only: function () {
		var editable = cint(this.frm.doc.payment_type !== "Pay");
		$.each(this.frm.get_field('instruments').grid.grid_rows || [], function (i, grid_row) {
			$.each(grid_row.docfields || [], function (i, df) {
				if (df.fieldname !== 'deposited') {
					grid_row.toggle_editable(df.fieldname, editable);
				}
			});
		});
	},

	get_undeposited_instruments: function () {
		var me = this;

		if (me.frm.doc.payment_type === "Pay" && me.frm.doc.vehicle_booking_order) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_payment.vehicle_booking_payment.get_undeposited_instruments",
				args: {
					vehicle_booking_order: me.frm.doc.vehicle_booking_order,
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
	},
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleBookingPayment({frm: cur_frm}));
