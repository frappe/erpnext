from frappe import _


def get_data():
	return {
		"fieldname": "demand_planning",
		"transactions": [
			{
				"label": _("MPS"),
				"items": ["Master Production Schedule"],
			},
		],
	}
