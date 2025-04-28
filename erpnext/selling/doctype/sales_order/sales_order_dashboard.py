from frappe import _


def get_data():
	return {
		"fieldname": "sales_order",
		"non_standard_fieldnames": {
			"Delivery Note": "against_sales_order",
			"Journal Entry": "reference_name",
			"Payment Entry": "reference_name",
			"Payment Request": "reference_name",
			"Auto Repeat": "reference_document",
			"Maintenance Visit": "prevdoc_docname",
			"Stock Reservation Entry": "voucher_no",
		},
		"internal_links": {
			"Quotation": ["items", "prevdoc_docname"],
<<<<<<< HEAD
			"BOM": ["items", "bom_no"],
			"Blanket Order": ["items", "blanket_order"],
			"Purchase Order": ["items", "purchase_order"],
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
		},
		"transactions": [
			{
				"label": _("Fulfillment"),
				"items": ["Sales Invoice", "Pick List", "Delivery Note", "Maintenance Visit"],
			},
			{"label": _("Purchasing"), "items": ["Material Request", "Purchase Order"]},
			{"label": _("Projects"), "items": ["Project"]},
<<<<<<< HEAD
			{"label": _("Manufacturing"), "items": ["Work Order", "BOM", "Blanket Order"]},
			{"label": _("Reference"), "items": ["Quotation", "Auto Repeat", "Stock Reservation Entry"]},
			{"label": _("Payment"), "items": ["Payment Entry", "Payment Request", "Journal Entry"]},
			{"label": _("Schedule"), "items": ["Delivery Schedule Item"]},
			{"label": _("Subcontracting Inward"), "items": ["Subcontracting Inward Order"]},
=======
			{"label": _("Manufacturing"), "items": ["Work Order"]},
			{"label": _("Reference"), "items": ["Quotation", "Auto Repeat", "Stock Reservation Entry"]},
			{"label": _("Payment"), "items": ["Payment Entry", "Payment Request", "Journal Entry"]},
>>>>>>> 7c4cf3e834 (Favicon.svg)
		],
	}
