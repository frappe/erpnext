from frappe import _


def get_data():
	return {
		"fieldname": "sales_forecast",
		"transactions": [
			{
				"label": _("MPS"),
				"items": ["Master Production Schedule"],
			},
		],
	}
