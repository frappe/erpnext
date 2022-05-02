from frappe import _


def get_data():
	return {
		"fieldname": "leave_period",
		"transactions": [{"label": _("Transactions"), "items": ["Leave Allocation"]}],
	}
