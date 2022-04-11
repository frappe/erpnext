from frappe import _


def get_data():
	return {
		"fieldname": "encounter",
		"non_standard_fieldnames": {
			"Patient Medical Record": "reference_name",
			"Inpatient Medication Order": "patient_encounter",
		},
		"transactions": [
			{"label": _("Records"), "items": ["Vital Signs", "Patient Medical Record"]},
			{"label": _("Orders"), "items": ["Inpatient Medication Order"]},
		],
		"disable_create_buttons": ["Inpatient Medication Order"],
	}
