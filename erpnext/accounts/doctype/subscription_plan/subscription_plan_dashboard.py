from frappe import _


def get_data():
	return {
		"fieldname": "subscription_plan",
		"non_standard_fieldnames": {"Payment Request": "plan", "Subscription": "plan"},
		"transactions": [{"label": _("References"), "items": ["Payment Request", "Subscription"]}],
	}
