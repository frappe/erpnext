from frappe import _

def get_data():
	return {
        "fieldname": "transporter_invoice_entry",
		"internal_links": {
			"Journal Entry": ["items", "reference"]
		},
		"transactions": [
			{"label": _("Related Transaction"), "items": ["Transporter Invoice","Journal Entry"]},
		],
	}