from frappe import _


def get_data():
	return {
		"fieldname": "time_sheet",
		"transactions": [{"label": _("References"), "items": ["Sales Invoice"]}],
	}
