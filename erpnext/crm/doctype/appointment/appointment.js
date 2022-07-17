// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.crm");

{% include 'erpnext/crm/doctype/appointment/appointment_slots.js' %};

erpnext.crm.AppointmentController = frappe.ui.form.Controller.extend({
	refresh: function() {
		erpnext.hide_company();
		this.make_appointment_slot_picker();
		this.setup_buttons();
	},

	setup_buttons: function () {
		if (this.frm.doc.lead) {
			this.frm.add_custom_button(this.frm.doc.lead, () => {
				frappe.set_route("Form", "Lead", this.frm.doc.lead);
			});
		}
		if (this.frm.doc.calendar_event) {
			this.frm.add_custom_button(__(this.frm.doc.calendar_event), () => {
				frappe.set_route("Form", "Event", this.frm.doc.calendar_event);
			});
		}
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

			this.set_scheduled_date_time();
			if (this.frm.doc.scheduled_date != previous_date) {
				this.reload_appointment_slot_picker();
			} else {
				this.refresh_appointment_slot_picker();
			}
		}
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
});

cur_frm.script_manager.make(erpnext.crm.AppointmentController);
