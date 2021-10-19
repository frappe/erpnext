// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");
erpnext.vehicles.VehicleInvoiceMovementController = erpnext.vehicles.VehicleTransactionController.extend({
	refresh: function () {
		this._super();
		this.frm.trigger('set_fields_read_only');
	},

	purpose: function () {
		this.frm.trigger('set_fields_read_only');
	},

	setup_queries: function () {
		this._super();

		var me = this;
		me.frm.set_query("vehicle", "invoices", function () {
			var filters = {};

			if (me.frm.doc.item_code) {
				filters['item_code'] = me.frm.doc.item_code;
			}
			if (me.frm.doc.supplier) {
				filters['supplier'] = ['in', ['', me.frm.doc.supplier]];
			}

			me.set_invoice_filter(filters);

			return {
				filters: filters
			}
		});

		me.frm.set_query("vehicle_booking_order", "invoices", function () {
			var filters = {
				docstatus: 1,
				status: ['!=', 'Cancelled Booking']
			}

			me.set_invoice_filter(filters);

			return {
				filters: filters
			};
		});
	},

	set_invoice_filter: function (filters) {
		if (this.frm.doc.purpose == "Receive") {
			filters['invoice_status'] = 'Not Received';
		} else if (this.frm.doc.purpose == "Return") {
			filters['invoice_status'] = 'Issued';
			if (this.frm.doc.issued_for) {
				filters['invoice_issued_for'] = this.frm.doc.issued_for;
			}
		} else {
			filters['invoice_status'] = 'In Hand';
		}
	},

	set_fields_read_only: function (doc, cdt, cdn) {
		var reqd = cint(this.frm.doc.purpose == "Receive");
		var read_only = cint(!reqd);
		this.frm.set_df_property('bill_no', 'read_only', read_only, cdn, 'invoices');
		this.frm.set_df_property('bill_no', 'reqd', reqd, cdn, 'invoices');
		this.frm.set_df_property('bill_date', 'read_only', read_only, cdn, 'invoices');
		this.frm.set_df_property('bill_date', 'reqd', reqd, cdn, 'invoices');
		this.frm.refresh_field('invoices');
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleInvoiceMovementController({frm: cur_frm}));
