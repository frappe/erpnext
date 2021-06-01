// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

{% include 'erpnext/selling/quotation_common.js' %}

erpnext.vehicles.VehicleQuotation = erpnext.vehicles.VehicleBookingController.extend({
	setup: function () {
		this.frm.custom_make_buttons = {
			'Vehicle Booking Order': 'Vehicle Booking Order'
		}
	},

	refresh: function () {
		this._super();
		this.set_dynamic_field_label();
		this.add_create_buttons();
	},

	setup_queries: function () {
		this._super();

		var me = this;

		me.frm.set_query("quotation_to", function () {
			return {
				"filters": {
					"name": ["in", ["Customer", "Lead"]],
				}
			}
		});

		me.frm.set_query("party_name", function () {
			if (me.frm.doc.quotation_to === "Customer") {
				return erpnext.queries.customer();
			} else if (me.frm.doc.quotation_to === "Lead") {
				return erpnext.queries.lead();
			}
		});
	},

	add_create_buttons: function () {
		if(this.frm.doc.docstatus == 1 && this.frm.doc.status !== 'Lost') {
			if(!this.frm.doc.valid_till || frappe.datetime.get_diff(this.frm.doc.valid_till, frappe.datetime.get_today()) >= 0) {
				this.frm.add_custom_button(__('Vehicle Booking Order'), () => this.make_vehicle_booking_order(), __('Create'));
			}

			if(this.frm.doc.status !== "Ordered") {
				this.frm.add_custom_button(__('Set as Lost'), () => {
					this.frm.trigger('set_as_lost_dialog');
				});
			}

			this.frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
	},

	quotation_to: function () {
		this.set_dynamic_field_label();
		this.frm.set_value("party_name", null);
	},

	party_name: function () {
		this.get_customer_details();
	},

	transaction_date: function () {
		this._super();
		this.set_valid_till();
	},

	quotation_validity_days: function () {
		this.set_valid_till();
	},

	valid_till: function () {
		this.set_quotation_validity_days();
	},

	set_valid_till: function() {
		if (this.frm.doc.transaction_date) {
			if (cint(this.frm.doc.quotation_validity_days) > 0) {
				this.frm.doc.valid_till = frappe.datetime.add_days(this.frm.doc.transaction_date, cint(this.frm.doc.quotation_validity_days)-1);
				this.frm.refresh_field('valid_till');
			} else if (this.frm.doc.valid_till && cint(this.frm.doc.quotation_validity_days) == 0) {
				this.set_quotation_validity_days();
			}
		}
	},

	set_quotation_validity_days: function () {
		if (this.frm.doc.transaction_date && this.frm.doc.valid_till) {
			var days = frappe.datetime.get_diff(this.frm.doc.valid_till, this.frm.doc.transaction_date) + 1;
			if (days > 0) {
				this.frm.doc.quotation_validity_days = days;
				this.frm.refresh_field('quotation_validity_days');
			}
		}
	},

	set_dynamic_field_label: function() {
		if (this.frm.doc.quotation_to) {
			this.frm.set_df_property("party_name", "label", __(this.frm.doc.quotation_to));
			this.frm.set_df_property("customer_address", "label", __(this.frm.doc.quotation_to + " Address"));
			this.frm.set_df_property("contact_person", "label", __(this.frm.doc.quotation_to + " Contact Person"));
		} else {
			this.frm.set_df_property("party_name", "label", __("Party"));
			this.frm.set_df_property("customer_address", "label", __("Party Address"));
			this.frm.set_df_property("contact_person", "label", __("Party Contact Person"));
		}
	},

	make_vehicle_booking_order: function () {
		frappe.model.open_mapped_doc({
			method: "erpnext.vehicles.doctype.vehicle_quotation.vehicle_quotation.make_vehicle_booking_order",
			frm: this.frm
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleQuotation({frm: cur_frm}));
