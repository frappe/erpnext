
frappe.views.calendar["Patient Appointment"] = {
	field_map: {
		"start": "start",
		"end": "end",
		"id": "name",
		"title": "patient",
		"allDay": "allDay",
		"eventColor": "color"
	},
	order_by: "appointment_date",
	gantt: true,
	get_events_method: "erpnext.healthcare.doctype.patient_appointment.patient_appointment.get_events"
};
