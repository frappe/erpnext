from frappe import _


def get_data(data):
	return {
		"fieldname": "workstation",
		"transactions": [
			{"label": _("Master"), "items": ["BOM", "Routing", "Operation"]},
			{
				"label": _("Transaction"),
				"items": [
					"Work Order",
					"Job Card",
				],
			},
		],
		"disable_create_buttons": [
			"BOM",
			"Routing",
			"Operation",
			"Work Order",
			"Job Card",
		],
	}
