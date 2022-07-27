// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.crm");

{% include 'erpnext/crm/doctype/appointment/appointment_slots.js' %};

erpnext.crm.AppointmentController = frappe.ui.form.Controller.extend({
	setup: function () {
		this.frm.custom_make_buttons = {
			'Project': 'Project',
			'Appointment': 'Reschedule',
		}
	},

	refresh: function() {
		erpnext.hide_company();
		this.make_appointment_slot_picker();
		this.setup_buttons();
		this.set_dynamic_field_label();
		this.set_dynamic_link();
		this.setup_route_options();
		this.set_applies_to_read_only();
	},

	onload: function () {
		this.setup_queries();
	},

	setup_buttons: function () {
		if (this.frm.doc.calendar_event) {
			this.frm.add_custom_button(__(this.frm.doc.calendar_event), () => {
				frappe.set_route("Form", "Event", this.frm.doc.calendar_event);
			});
		}

		var customer;
		if (this.frm.doc.appointment_for == "Customer") {
			customer = this.frm.doc.party_name;
		} else if (this.frm.doc.appointment_for == "Lead") {
			customer = this.frm.doc.__onload && this.frm.doc.__onload.customer;
		}

		if(this.frm.doc.docstatus == 1 && this.frm.doc.status != "Rescheduled") {
			if (["Open", "Missed"].includes(this.frm.doc.status)) {
				this.frm.add_custom_button(__('Reschedule'), () => this.reschedule_appointment(),
					__("Set Status"));
			}

			if (this.frm.doc.status != "Missed") {
				this.frm.add_custom_button(__('Missed'), () => this.update_status("Missed"),
					__("Set Status"));
			}

			if (this.frm.doc.status != "Closed") {
				this.frm.add_custom_button(__('Closed'), () => this.update_status("Closed"),
					__("Set Status"));
			}

			if ((this.frm.doc.status == "Closed" && this.frm.doc.is_closed) || this.frm.doc.status == "Missed") {
				this.frm.add_custom_button(__('Re-Open'), () => this.update_status("Open"),
					__("Set Status"));
			}

			// Create Buttons
			if (!customer) {
				this.frm.add_custom_button(__('Customer'), () => {
					erpnext.utils.make_customer_from_lead(this.frm, this.frm.doc.party_name);
				}, __('Create'));
			}

			this.frm.add_custom_button(__('Project'), () => this.make_project(),
				__('Create'));

			this.frm.page.set_inner_btn_group_as_primary(__('Create'));
		}
	},

	setup_queries: function () {
		var me = this;

		me.frm.set_query("appointment_for", function () {
			return {
				"filters": {
					"name": ["in", ["Customer", "Lead"]],
				}
			}
		});

		me.frm.set_query("party_name", function () {
			if (me.frm.doc.appointment_for === "Customer") {
				return erpnext.queries.customer();
			} else if (me.frm.doc.appointment_for === "Lead") {
				return erpnext.queries.lead();
			}
		});

		me.frm.set_query('customer_address', () => {
			return erpnext.queries.address_query(me.frm.doc);
		});
		me.frm.set_query('contact_person', () => {
			return erpnext.queries.contact_query(me.frm.doc);
		});
	},

	setup_route_options: function () {
		var me = this;
		var vehicle_field = me.frm.get_docfield("applies_to_vehicle");
		if (vehicle_field) {
			vehicle_field.get_route_options_for_new_doc = function () {
				return {
					"item_code": me.frm.doc.applies_to_item,
					"item_name": me.frm.doc.applies_to_item_name,
					"unregistered": me.frm.doc.vehicle_unregistered,
					"license_plate": me.frm.doc.vehicle_license_plate,
					"chassis_no": me.frm.doc.vehicle_chassis_no,
					"engine_no": me.frm.doc.vehicle_engine_no,
					"color": me.frm.doc.vehicle_color,
				}
			}
		}
	},

	set_dynamic_link: function () {
		var doctype = this.frm.doc.appointment_for == 'Lead' ? 'Lead' : 'Customer';
		frappe.dynamic_link = {doc: this.frm.doc, fieldname: 'party_name', doctype: doctype}
	},

	scheduled_date: function () {
		this.set_scheduled_date_time();
		this.reload_appointment_slot_picker();
	},
	scheduled_time: function () {
		this.set_scheduled_date_time();
		this.refresh_appointment_slot_picker()
	},
	appointment_duration: function () {
		this.set_scheduled_date_time();
		this.refresh_appointment_slot_picker()
	},

	appointment_type: function () {
		this.reload_appointment_slot_picker();
	},

	set_scheduled_timeslot: function (timeslot_start, timeslot_duration) {
		if (timeslot_start) {
			var previous_date = this.frm.doc.scheduled_date;
			var timeslot_start_obj = frappe.datetime.str_to_obj(timeslot_start);

			this.frm.doc.scheduled_date = moment(timeslot_start_obj).format(frappe.defaultDateFormat);
			this.frm.doc.scheduled_time = moment(timeslot_start_obj).format(frappe.defaultTimeFormat);
			this.frm.doc.appointment_duration = cint(timeslot_duration);

			this.frm.refresh_field('scheduled_date');
			this.frm.refresh_field('scheduled_time');
			this.frm.refresh_field('appointment_duration');
			this.frm.dirty();

			this.set_scheduled_date_time();
			if (this.frm.doc.scheduled_date != previous_date) {
				this.reload_appointment_slot_picker();
			} else {
				this.refresh_appointment_slot_picker();
			}
		}
	},

	set_scheduled_date_time: function () {
		if (this.frm.doc.scheduled_date) {
			var scheduled_date_obj = frappe.datetime.str_to_obj(this.frm.doc.scheduled_date);
			this.frm.doc.scheduled_day_of_week = moment(scheduled_date_obj).format('dddd');
		} else {
			this.frm.doc.scheduled_day_of_week = null;
		}

		if (this.frm.doc.scheduled_date && this.frm.doc.scheduled_time) {
			var scheduled_dt_obj = frappe.datetime.str_to_obj(this.frm.doc.scheduled_date + " " + this.frm.doc.scheduled_time);
			var scheduled_dt_str = frappe.datetime.get_datetime_as_string(scheduled_dt_obj);

			var end_dt_obj = moment(scheduled_dt_obj).add(cint(this.frm.doc.appointment_duration), 'minutes').toDate();
			var end_dt_str = frappe.datetime.get_datetime_as_string(end_dt_obj);

			this.frm.doc.scheduled_dt = scheduled_dt_str;
			this.frm.doc.end_dt = end_dt_str;
		} else {
			this.frm.doc.scheduled_dt = null;
			this.frm.doc.end_dt = null;
		}

		this.frm.refresh_field('scheduled_dt');
		this.frm.refresh_field('end_dt');
		this.frm.refresh_field('scheduled_day_of_week');
	},

	make_appointment_slot_picker: function () {
		if (this.frm.fields_dict.appointment_slot_picker_html) {
			this.frm.appointment_slot_picker = erpnext.crm.make_appointment_slot_picker(this.frm,
				this.frm.fields_dict.appointment_slot_picker_html.wrapper);
		}
	},

	reload_appointment_slot_picker: function () {
		if (this.frm.appointment_slot_picker) {
			this.frm.appointment_slot_picker.load_slots_and_render();
		}
	},

	refresh_appointment_slot_picker: function () {
		if (this.frm.appointment_slot_picker) {
			this.frm.appointment_slot_picker.render_slot_picker();
		}
	},

	appointment_for: function () {
		this.set_dynamic_field_label();
		this.set_dynamic_link();
		this.frm.set_value("party_name", null);
	},

	party_name: function () {
		this.get_customer_details();
	},

	contact_person: function() {
		erpnext.utils.get_contact_details(this.frm);
	},
	customer_address: function() {
		erpnext.utils.get_address_display(this.frm, "customer_address");
	},

	get_customer_details: function () {
		var me = this;

		if (me.frm.doc.company && me.frm.doc.appointment_for && me.frm.doc.party_name) {
			frappe.call({
				method: "erpnext.crm.doctype.appointment.appointment.get_customer_details",
				args: {
					args: {
						doctype: me.frm.doc.doctype,
						company: me.frm.doc.company,
						appointment_for: me.frm.doc.appointment_for,
						party_name: me.frm.doc.party_name,
					}
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						me.frm.set_value(r.message);
					}
				}
			});
		}
	},

	set_dynamic_field_label: function () {
		if (this.frm.doc.appointment_for) {
			this.frm.set_df_property("party_name", "label", __(this.frm.doc.appointment_for));
			this.frm.set_df_property("customer_address", "label", __(this.frm.doc.appointment_for + " Address"));
			this.frm.set_df_property("contact_person", "label", __(this.frm.doc.appointment_for + " Contact Person"));
		} else {
			this.frm.set_df_property("party_name", "label", __("Party"));
			this.frm.set_df_property("customer_address", "label", __("Address"));
			this.frm.set_df_property("contact_person", "label", __("Contact Person"));
		}
	},

	applies_to_item: function () {
		this.get_applies_to_details();
	},
	applies_to_vehicle: function () {
		this.set_applies_to_read_only();
		this.get_applies_to_details();
	},

	vehicle_chassis_no: function () {
		erpnext.utils.format_vehicle_id(this.frm, 'vehicle_chassis_no');
	},
	vehicle_engine_no: function () {
		erpnext.utils.format_vehicle_id(this.frm, 'vehicle_engine_no');
	},
	vehicle_license_plate: function () {
		erpnext.utils.format_vehicle_id(this.frm, 'vehicle_license_plate');
	},

	get_applies_to_details: function () {
		var me = this;
		var args = this.get_applies_to_args();
		return frappe.call({
			method: "erpnext.stock.get_item_details.get_applies_to_details",
			args: {
				args: args
			},
			callback: function(r) {
				if(!r.exc) {
					return me.frm.set_value(r.message);
				}
			}
		});
	},

	get_applies_to_args: function () {
		return {
			applies_to_item: this.frm.doc.applies_to_item,
			applies_to_vehicle: this.frm.doc.applies_to_vehicle,
			doctype: this.frm.doc.doctype,
			name: this.frm.doc.name,
		}
	},

	set_applies_to_read_only: function() {
		var me = this;
		var read_only_fields = [
			'applies_to_item', 'applies_to_item_name',
			'vehicle_license_plate', 'vehicle_unregistered',
			'vehicle_chassis_no', 'vehicle_engine_no',
			'vehicle_color', 'vehicle_last_odometer',
		];
		$.each(read_only_fields, function (i, f) {
			if (me.frm.fields_dict[f]) {
				me.frm.set_df_property(f, "read_only", me.frm.doc.applies_to_vehicle ? 1 : 0);
			}
		});
	},

	make_project: function () {
		this.frm.check_if_unsaved();
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.appointment.appointment.get_project",
			frm: this.frm
		});
	},

	reschedule_appointment: function () {
		this.frm.check_if_unsaved();
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.appointment.appointment.get_rescheduled_appointment",
			frm: this.frm
		});
	},

	update_status: function(status) {
		var me = this;
		me.frm.check_if_unsaved();

		frappe.call({
			method: "erpnext.crm.doctype.appointment.appointment.update_status",
			args: {
				appointment: me.frm.doc.name,
				status: status
			},
			callback: function(r) {
				me.frm.reload_doc();
			},
		});
	},
});

cur_frm.script_manager.make(erpnext.crm.AppointmentController);
