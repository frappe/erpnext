from frappe import _


def get_data():
	return {
		"fieldname": "template",
		"transactions": [
			{"label": _("Rules"), "items": ["Product Configuration Rule"]},
			{"label": _("Configurations"), "items": ["Product Configuration"]},
		],
	}
