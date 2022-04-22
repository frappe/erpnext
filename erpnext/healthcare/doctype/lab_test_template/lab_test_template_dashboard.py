from frappe import _


def get_data():
	return {
		"fieldname": "template",
		"transactions": [{"label": _("Lab Tests"), "items": ["Lab Test"]}],
	}
