// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleDeliveryController = erpnext.vehicles.VehicleTransactionController.extend({
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

			return {
				filters: filters
			}
		});

		this.frm.set_query("vehicle_booking_order", function() {
			return {
				filters: {
					docstatus: 1,
					status: ['!=', 'Cancelled Booking'],
					delivery_status: 'To Deliver'
				}
			};
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleDeliveryController({frm: cur_frm}));
