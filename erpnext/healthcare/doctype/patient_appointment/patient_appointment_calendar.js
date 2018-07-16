
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
	get_events_method: "erpnext.healthcare.doctype.patient_appointment.patient_appointment.get_events",
	filters: [
		{
			'fieldtype': 'Link',
			'fieldname': 'practitioner',
			'options': 'Healthcare Practitioner',
			'label': __('Healthcare Practitioner')
		},
		{
			'fieldtype': 'Link',
			'fieldname': 'patient',
			'options': 'Patient',
			'label': __('Patient')
		},
		{
			'fieldtype': 'Link',
			'fieldname': 'appointment_type',
			'options': 'Appointment Type',
			'label': __('Appointment Type')
		},
		{
			'fieldtype': 'Link',
			'fieldname': 'department',
			'options': 'Medical Department',
			'label': __('Department')
		},
		{
			'fieldtype': 'Select',
			'fieldname': 'status',
			'options': 'Scheduled\nOpen\nClosed\nPending',
			'label': __('Status')
		}
	]
};
