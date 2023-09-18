from frappe import _


def get_data():
	return {
		"heatmap": True,
		"heatmap_message": _("This covers all scorecards tied to this Setup"),
		"fieldname": "party",
		"method": "erpnext.risk.doctype.scorecard.scorecard.get_timeline_data",
		"transactions": [{"label": _("Scorecards"), "items": ["Scorecard Period"]}],
	}
