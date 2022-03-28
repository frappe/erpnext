from frappe import _


def get_data():
	return {
		"fieldname": "leave_policy_assignment",
		"transactions": [
			{"label": _("Leaves"), "items": ["Leave Allocation"]},
		],
	}
