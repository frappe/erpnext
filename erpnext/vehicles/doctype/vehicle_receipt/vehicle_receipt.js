// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleReceiptController = erpnext.vehicles.VehicleTransactionController.extend({
	refresh: function () {
		this._super();
		this.show_stock_ledger()
	},

	setup_queries: function () {
		this._super();

		var me = this;
		this.frm.set_query("vehicle", function () {
			var filters = {
				item_code: me.frm.doc.item_code,
				warehouse: ['is', 'not set'],
				purchase_document_no: ['is', 'not set']
			};

			if (me.frm.doc.supplier) {
				filters['supplier'] = ['in', ['', me.frm.doc.supplier]];
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
					delivery_status: 'Not Received'
				}
			};
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleReceiptController({frm: cur_frm}));
