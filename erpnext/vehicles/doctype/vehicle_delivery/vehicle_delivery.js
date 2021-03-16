// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/vehicles/vehicle_transaction_common.js' %}

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleDeliveryController = erpnext.vehicles.VehiclesController.extend({
	refresh: function () {
		this._super();
		this.show_stock_ledger()
	},

	setup_queries: function () {
		this._super();

		var me = this;
		this.frm.set_query("vehicle", function () {
			var filters = {item_code: me.frm.doc.item_code};
			if (me.frm.doc.warehouse) {
				filters['warehouse'] = me.frm.doc.warehouse;
			} else {
				filters['warehouse'] = ['is', 'set'];
			}

			if (me.frm.doc.vehicle_booking_order) {
				filters['is_booked'] = 1;
			}

			return {
				filters: filters
			}
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleDeliveryController({frm: cur_frm}));
