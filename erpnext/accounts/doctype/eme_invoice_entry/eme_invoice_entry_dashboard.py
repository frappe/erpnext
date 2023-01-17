from frappe import _

def get_data():
	return {
        "fieldname": "eme_invoice_entry",
		"internal_links": {
			"Journal Entry": ["successful_transaction", "reference_name"]
		},
		"transactions": [
			{"label": _("Related Transaction"), "items": ["EME Invoice","Journal Entry"]},
		],
	}