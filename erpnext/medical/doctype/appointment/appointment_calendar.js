
frappe.views.calendar["Appointment"] = {
	field_map: {
		"start": "start_dt",
		"end": "end_dt",
		"id": "name",
		"title": "patient",
		"allDay": "allDay"
	},
	gantt: true,
	get_events_method: "erpnext.medical.doctype.appointment.appointment.get_events",
	filters: [
		{
			'fieldtype': 'Link',
			'fieldname': 'physician',
			'options': 'Physician',
			'label': __('Physician')
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
}
