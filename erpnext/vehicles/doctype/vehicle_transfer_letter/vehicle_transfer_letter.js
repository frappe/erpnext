// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/vehicles/vehicle_transaction_controller.js' %}

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleTransferLetterController = erpnext.vehicles.VehicleTransactionController.extend({
	refresh: function () {
		this._super();
	},

	setup_queries: function () {
		this._super();

		var me = this;
		this.frm.set_query("vehicle", function () {
			var filters = {item_code: me.frm.doc.item_code};

			if (me.frm.doc.vehicle_booking_order) {
				filters['is_booked'] = 1;
			}

			return {
				filters: filters
			}
		});

		this.frm.set_query("vehicle_booking_order", function() {
			return {
				filters: {
					docstatus: 1,
					vehicle: ['is', 'set']
				}
			};
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleTransferLetterController({frm: cur_frm}));
