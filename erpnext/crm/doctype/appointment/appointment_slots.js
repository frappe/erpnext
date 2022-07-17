frappe.provide("erpnext.crm");

erpnext.crm.make_appointment_slot_picker = function (frm, wrapper, title) {
	$(wrapper).empty();
	if (title) {
		$(`<label class="control-label">${title}</label>`).appendTo(wrapper);
	}
	var slotpicker_area = $('<div></div>').appendTo(wrapper);
	return new erpnext.crm.AppointmentSlotPicker(frm, slotpicker_area);
};

erpnext.crm.AppointmentSlotPicker = Class.extend({
	init: function(frm, wrapper) {
		var me = this;

		me.frm = frm;

		me.wrapper = $(wrapper);
		me.slot_picker_wrapper = $(`<div class="row slot-picker"></div>`).appendTo(me.wrapper);
		me.message_wrapper = $(`<div></div>`).appendTo(me.wrapper);

		me.timeslots = [];
		me.load_slots_and_render();
		me.bind();
	},

	load_slots_and_render: function () {
		var me = this;

		if (me.frm.doc.scheduled_date && me.frm.doc.appointment_type) {
			frappe.call({
				method: "erpnext.crm.doctype.appointment.appointment.get_appointment_timeslots",
				args: {
					scheduled_date: me.frm.doc.scheduled_date,
					appointment_type: me.frm.doc.appointment_type,
					appointment: me.frm.is_new() ? null : me.frm.doc.name,
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						me.timeslots = r.message;
						me.render_slot_picker();
					}
				}
			});
		} else {
			me.timeslots = [];
			me.render_slot_picker();
		}
	},

	render_slot_picker: function () {
		if (this.frm.doc.scheduled_date && this.frm.doc.appointment_type) {
			if (this.timeslots && this.timeslots.length) {
				this.render_slots();
			} else if (this.timeslots) {
				this.render_message(__("No timeslots available on {0} for Appointment Type {1}.",
					[moment(this.frm.doc.scheduled_date).format('dddd, D MMMM, YYYY'), this.frm.doc.appointment_type]));
			} else {
				this.render_message(__("No timeslots configured for Appointment Type {0}.",
					[this.frm.doc.appointment_type]));
			}
		} else {
			this.render_message(__("Please select Appointment Type and Schedule Date to see available time slots."));
		}
	},

	render_slots: function() {
		var me = this;
		me.clear();

		var container = $(`<div class='container-fluid'></div>`).appendTo(me.slot_picker_wrapper);
		var row = $(`<div class='row'></div>`).appendTo(container);

		$.each(me.timeslots || [], function (i, slot) {
			// indicator
			var indicator_color;
			if (slot.available > 0) {
				if (slot.booked > 0) {
					indicator_color = "blue";
				} else {
					indicator_color = "green";
				}
			} else {
				indicator_color = "darkgrey";
			}

			// panel styling
			var muted = "";
			if (slot.available <= 0) {
				muted = "text-muted";
			}

			var panel_class = "panel-default";
			if (me.timeslot_in_scheduled_time(slot)) {
				panel_class = "panel-primary";
			}

			// availability text
			var availability_text;
			if (slot.available > 0) {
				availability_text = `<b>${slot.available}</b> ${__("Available")}`;
			} else {
				availability_text = __("Unavailable");
			}

			// booked text
			var booked_text;
			if (slot.booked > 0) {
				booked_text = `<b>${slot.booked}</b> ${__("Booked")}`;
			} else {
				booked_text = __("Not Booked");
			}

			var slot_html = `
			<div class="col-md-2 col-sm-3 col-xs-6">
				<div class="panel ${panel_class} ${muted} appointment-timeslot"
						data-timeslot-start="${slot.timeslot_start}"
						data-timeslot-end="${slot.timeslot_end}"
						data-timeslot-duration="${slot.timeslot_duration}">
					<div class="panel-body text-center" style="padding: 10px;">
						<div class="panel-title">
							<span class="indicator ${indicator_color}" style="font-size: 15px; color: inherit">
								${moment(slot.timeslot_start).format('hh:mm A')}
							</span>
						</div>

						<div class="small">till ${moment(slot.timeslot_end).format('hh:mm A')}</div>

						<hr style="margin-top: 5px; margin-bottom: 5px;">

						<div class="small">${availability_text}</div>
						<div class="small">${booked_text}</div>
					</div>
				</div>
			</div>
			`;
			$(slot_html).appendTo(row);
		});
	},

	render_message: function (message) {
		this.clear();
		this.message_wrapper.text(message);
	},

	clear: function () {
		this.slot_picker_wrapper.empty();
		this.message_wrapper.empty();
	},

	timeslot_in_scheduled_time: function (slot) {
		if (!this.frm.doc.scheduled_dt || !this.frm.doc.end_dt) {
			return false;
		}

		return moment(slot.timeslot_start).isBefore(moment(this.frm.doc.end_dt))
			&& moment(slot.timeslot_end).isAfter(moment(this.frm.doc.scheduled_dt));
	},

	bind: function () {
		var me = this;
		me.slot_picker_wrapper.on("click", ".appointment-timeslot", function () {
			me.on_timeslot_click(this);
		});
	},

	on_timeslot_click: function (el) {
		var timeslot_start = $(el).attr('data-timeslot-start');
		var timeslot_duration = cint($(el).attr('data-timeslot-duration'));

		if (timeslot_start && timeslot_duration) {
			this.frm.cscript.set_scheduled_timeslot(timeslot_start, timeslot_duration);
		}
	},
});
