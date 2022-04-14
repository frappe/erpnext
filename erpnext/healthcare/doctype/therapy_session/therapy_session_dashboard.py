from frappe import _


def get_data():
	return {
		"fieldname": "therapy_session",
		"transactions": [{"label": _("Assessments"), "items": ["Patient Assessment"]}],
	}
