from frappe import _


def get_data():
	return {
		"heatmap": True,
		"heatmap_message": _(
			"This is based on transactions against this Patient. See timeline below for details"
		),
		"fieldname": "patient",
		"non_standard_fieldnames": {"Payment Entry": "party"},
		"transactions": [
			{
				"label": _("Appointments and Encounters"),
				"items": ["Patient Appointment", "Vital Signs", "Patient Encounter"],
			},
			{"label": _("Lab Tests and Vital Signs"), "items": ["Lab Test", "Sample Collection"]},
			{
				"label": _("Rehab and Physiotherapy"),
				"items": ["Patient Assessment", "Therapy Session", "Therapy Plan"],
			},
			{"label": _("Surgery"), "items": ["Clinical Procedure"]},
			{"label": _("Admissions"), "items": ["Inpatient Record", "Inpatient Medication Order"]},
			{"label": _("Billing and Payments"), "items": ["Sales Invoice", "Payment Entry"]},
		],
	}
