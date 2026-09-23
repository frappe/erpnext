from frappe import _


def get_data():
	return {
		"heatmap": True,
		"heatmap_message": _("This covers all scorecards tied to this Setup"),
		"fieldname": "supplier",
		"transactions": [{"label": _("Scorecards"), "items": ["Supplier Scorecard Period"]}],
	}
