from frappe import _


def get_data():
	return {
		"fieldname": "prevdoc_docname",
		"method": "erpnext.selling.doctype.quotation.quotation.get_open_count",
		"non_standard_fieldnames": {
			"Auto Repeat": "reference_document",
			"Quotation": "revision_of",
		},
		"transactions": [
			{"label": _("Sales Order"), "items": ["Sales Order"]},
			{"label": _("Subscription"), "items": ["Auto Repeat"]},
			{"label": _("Versions"), "items": ["Quotation"]},
		],
	}
