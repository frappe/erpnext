// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

{% include 'erpnext/selling/quotation_common.js' %}

erpnext.vehicles.VehicleQuotation = class VehicleQuotation extends erpnext.vehicles.VehicleBookingController {
	setup() {
		this.frm.custom_make_buttons = {
			'Vehicle Booking Order': 'Vehicle Booking Order',
			'Customer': 'Customer'
		}
	}

	refresh() {
		super.refresh();
		this.set_dynamic_field_label();
		this.add_create_buttons();
	}

	setup_queries() {
		super.setup_queries();

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
	}

	add_create_buttons() {
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
					this.frm.trigger('set_as_lost_dialog');
				});
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
	}

	quotation_to() {
		this.set_dynamic_field_label();
		this.frm.set_value("party_name", null);
	}

	party_name() {
		this.get_customer_details();
	}

	set_dynamic_field_label() {
		if (this.frm.doc.quotation_to) {
			this.frm.set_df_property("party_name", "label", __(this.frm.doc.quotation_to));
			this.frm.set_df_property("customer_address", "label", __(this.frm.doc.quotation_to + " Address"));
			this.frm.set_df_property("contact_person", "label", __(this.frm.doc.quotation_to + " Contact Person"));
		} else {
			this.frm.set_df_property("party_name", "label", __("Party"));
			this.frm.set_df_property("customer_address", "label", __("Party Address"));
			this.frm.set_df_property("contact_person", "label", __("Party Contact Person"));
		}
	}

	make_vehicle_booking_order() {
		frappe.model.open_mapped_doc({
			method: "erpnext.vehicles.doctype.vehicle_quotation.vehicle_quotation.make_vehicle_booking_order",
			frm: this.frm
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.vehicles.VehicleQuotation({frm: cur_frm}));
