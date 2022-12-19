// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.crm");

{% include 'erpnext/crm/doctype/appointment/appointment_slots.js' %};
{% include 'erpnext/vehicles/customer_vehicle_selector.js' %};
{% include 'erpnext/public/js/controllers/quick_contacts.js' %};
{% include 'erpnext/stock/applies_to_common.js' %};

erpnext.crm.AppointmentController = erpnext.contacts.QuickContacts.extend({
	setup: function () {
		this.frm.custom_make_buttons = {
			'Project': 'Project',
			'Appointment': 'Reschedule',
		}
	},

	refresh: function() {
		erpnext.hide_company();
		this.setup_buttons();
		this.set_dynamic_field_label();
		this.set_dynamic_link();

		this.frm.trigger('set_disallow_on_submit_fields_read_only');
		this.setup_dashboard();

		this.make_appointment_slot_picker();
		this.make_customer_vehicle_selector();
	},

	onload: function () {
		this._super();
		this.setup_queries();
	},

	setup_buttons: function () {
		this.setup_notification_buttons();

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

	setup_notification_buttons: function() {
		if(this.frm.doc.docstatus === 1) {
			if (this.can_notify("Appointment Confirmation")) {
				var confirmation_count = frappe.get_notification_count(this.frm, 'Appointment Confirmation', 'SMS');
				let label = __("Appointment Confirmation{0}", [confirmation_count ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Appointment Confirmation'),
					__("Notify"));
			}

			if (this.can_notify("Appointment Reminder")) {
				var reminder_count = frappe.get_notification_count(this.frm, 'Appointment Reminder', 'SMS');
				let label = __("Appointment Reminder{0}", [reminder_count ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Appointment Reminder'),
					__("Notify"));
			}
		}

		if (this.frm.doc.docstatus === 2) {
			if (this.can_notify("Appointment Cancellation")) {
				var cancellation_count = frappe.get_notification_count(this.frm, 'Appointment Cancellation', 'SMS');
				let label = __("Appointment Cancellation{0}", [cancellation_count ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Appointment Cancellation'),
					__("Notify"));
			}
		}

		if (this.frm.doc.docstatus != 0) {
			this.frm.add_custom_button(__("Custom Message"), () => this.send_sms('Custom Message'),
				__("Notify"));
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

		me.frm.set_query('secondary_contact_person', () => {
			return erpnext.queries.contact_query(me.frm.doc);
		});
	},

	setup_dashboard: function() {
		if (this.frm.doc.docstatus == 0) {
			return;
		}

		var me = this;

		// Notification Status
		var confirmation_count = frappe.get_notification_count(me.frm, 'Appointment Confirmation', 'SMS');
		var confirmation_color = confirmation_count ? "green"
			: this.can_notify('Appointment Confirmation') ? "yellow" : "grey";
		var confirmation_status = confirmation_count ? __("{0} SMS", [confirmation_count])
			: __("Not Sent");

		var reminder_count = frappe.get_notification_count(me.frm, 'Appointment Reminder', 'SMS');
		var reminder_status = __("Not Sent");
		var reminder_color = "grey";

		if (reminder_count) {
			reminder_color = "green";
			reminder_status = __("{0} SMS", [reminder_count]);
		} else if (me.frm.doc.__onload && me.frm.doc.__onload.scheduled_reminder) {
			var scheduled_reminder_str = frappe.datetime.str_to_user(me.frm.doc.__onload.scheduled_reminder);
			reminder_color = "blue";
			reminder_status = __("Scheduled ({0})", [scheduled_reminder_str]);
		}

		var cancellation_count = frappe.get_notification_count(me.frm, 'Appointment Cancellation', 'SMS');
		var cancellation_color = cancellation_count ? "green"
			: this.can_notify('Appointment Cancellation') ? "yellow" : "grey";
		var cancellation_status = cancellation_count ? __("{0} SMS", [cancellation_count])
			: __("Not Sent");

		me.frm.dashboard.add_indicator(__('Appointment Confirmation: {0}', [confirmation_status]), confirmation_color);
		me.frm.dashboard.add_indicator(__('Appointment Reminder: {0}', [reminder_status]), reminder_color);
		if (me.frm.doc.docstatus == 2) {
			me.frm.dashboard.add_indicator(__('Appointment Cancellation: {0}', [cancellation_status]), cancellation_color);
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

	make_customer_vehicle_selector: function () {
		if (this.frm.fields_dict.customer_vehicle_selector_html) {
			this.frm.customer_vehicle_selector = erpnext.vehicles.make_customer_vehicle_selector(this.frm,
				this.frm.fields_dict.customer_vehicle_selector_html.wrapper,
				'applies_to_vehicle',
				'party_name',
				'appointment_for'
			);
		}
	},

	reload_customer_vehicle_selector: function () {
		if (this.frm.customer_vehicle_selector) {
			this.frm.customer_vehicle_selector.load_and_render();
		}
	},

	appointment_for: function () {
		this.set_dynamic_field_label();
		this.set_dynamic_link();
		this.frm.set_value("party_name", null);
		this.reload_customer_vehicle_selector();
	},

	party_name: function () {
		this.get_customer_details();
		this.reload_customer_vehicle_selector();
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
						frappe.run_serially([
							() => me.frm.set_value(r.message),
							() => me.setup_contact_no_fields(r.message.contact_nos),
						]);
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

	applies_to_vehicle: function () {
		this.reload_customer_vehicle_selector();
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

	can_notify: function (what) {
		if (this.frm.doc.__onload && this.frm.doc.__onload.can_notify) {
			return this.frm.doc.__onload.can_notify[what];
		} else {
			return false;
		}
	},

	send_sms: function(notification_type) {
		new frappe.SMSManager(this.frm.doc, {
			notification_type: notification_type,
			mobile_no: this.frm.doc.contact_mobile,
			party_doctype: this.frm.doc.appointment_for,
			party: this.frm.doc.party_name,
		});
	},
});

cur_frm.script_manager.make(erpnext.crm.AppointmentController);
