from frappe import _


def get_data():
	return {
		"heatmap": True,
		"heatmap_message": _(
			"This is based on transactions against this Supplier. See timeline below for details"
		),
		"fieldname": "supplier",
		"non_standard_fieldnames": {"Payment Entry": "party", "Bank Account": "party"},
		"transactions": [
			{"label": _("Procurement"), "items": ["Request for Quotation", "Supplier Quotation"]},
			{"label": _("Orders"), "items": ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]},
			{"label": _("Payments"), "items": ["Payment Entry", "Bank Account"]},
			{"label": _("Pricing"), "items": ["Pricing Rule"]},
		],
	}
