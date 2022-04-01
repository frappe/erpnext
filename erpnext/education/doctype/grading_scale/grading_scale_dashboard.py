from frappe import _


def get_data():
	return {
		"fieldname": "grading_scale",
		"non_standard_fieldnames": {"Course": "default_grading_scale"},
		"transactions": [
			{"label": _("Course"), "items": ["Course"]},
			{"label": _("Assessment"), "items": ["Assessment Plan", "Assessment Result"]},
		],
	}
