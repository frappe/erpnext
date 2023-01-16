from frappe import _

def get_data():
	return {
        "fieldname": "transporter_invoice_entry",
		"internal_links": {
			"Payment Entry": ["items", "reference_name"]
		},
		"transactions": [
			{"label": _("Related Transaction"), "items": ["Transporter Invoice","Payment Entry"]},
		],
	}