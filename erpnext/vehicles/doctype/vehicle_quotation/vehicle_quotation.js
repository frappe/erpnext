// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

{% include 'erpnext/selling/quotation_common.js' %}

erpnext.vehicles.VehicleQuotation = erpnext.vehicles.VehicleBookingController.extend({
	setup: function () {
		this.frm.custom_make_buttons = {
			'Vehicle Booking Order': 'Vehicle Booking Order',
			'Customer': 'Customer'
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
		var is_valid = !this.frm.doc.valid_till || frappe.datetime.get_diff(this.frm.doc.valid_till, frappe.datetime.get_today()) >= 0;

		var customer;
		if (this.frm.doc.quotation_to == "Customer") {
			customer = this.frm.doc.party_name;
		} else if (this.frm.doc.quotation_to == "Lead") {
			customer = this.frm.doc.__onload && this.frm.doc.__onload.customer;
		}

		if(this.frm.doc.docstatus == 1 && this.frm.doc.status !== 'Lost') {
			if(this.frm.doc.status !== "Ordered") {
				this.frm.add_custom_button(__('Set as Lost'), () => {
					this.frm.events.set_as_lost_dialog(this.frm);
				}, __("Status"));
			}

			if (!customer) {
				this.frm.add_custom_button(__('Customer'), () => {
					erpnext.utils.make_customer_from_lead(this.frm, this.frm.doc.party_name);
				}, __('Create'));
			}

			if (is_valid) {
				this.frm.add_custom_button(__('Vehicle Booking Order'), () => this.make_vehicle_booking_order(), __('Create'));
			}

			this.frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		if (this.frm.doc.status == "Lost") {
			me.frm.add_custom_button(__("Reopen"), () => {
				me.frm.events.update_lost_status(me.frm, 'Open');
			}, __("Status"));
		}

	},

	quotation_to: function () {
		this.set_dynamic_field_label();
		this.frm.set_value("party_name", null);
	},

	party_name: function () {
		this.get_customer_details();
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
	},
});

$.extend(cur_frm.cscript, new erpnext.vehicles.VehicleQuotation({frm: cur_frm}));
