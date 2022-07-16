// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.crm");

erpnext.crm.AppointmentController = frappe.ui.form.Controller.extend({
	refresh: function() {
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

	scheduled_date: function () {
		this.set_scheduled_dt();
	},
	scheduled_time: function () {
		this.set_scheduled_dt();
	},

	set_scheduled_dt: function () {
		if (this.frm.doc.scheduled_date && this.frm.doc.scheduled_time) {
			var datetime = frappe.datetime.str_to_obj(this.frm.doc.scheduled_date + " " + this.frm.doc.scheduled_time);
			var datetime_str = frappe.datetime.get_datetime_as_string(datetime);
			this.frm.set_value('scheduled_dt', datetime_str);
		} else {
			this.frm.set_value('scheduled_dt', null);
		}
	}
});

cur_frm.script_manager.make(erpnext.crm.AppointmentController);
