from frappe import _


def get_data():
	return {
		"fieldname": "purchase_order",
		"non_standard_fieldnames": {
			"Journal Entry": "reference_name",
			"Payment Entry": "reference_name",
			"Payment Request": "reference_name",
			"Auto Repeat": "reference_document",
		},
		"internal_links": {
			"Material Request": ["items", "material_request"],
			"Supplier Quotation": ["items", "supplier_quotation"],
			"Project": ["items", "project"],
<<<<<<< HEAD
			"Sales Order": ["items", "sales_order"],
			"BOM": ["items", "bom"],
			"Production Plan": ["items", "production_plan"],
			"Blanket Order": ["items", "blanket_order"],
		},
		"transactions": [
			{"label": _("Related"), "items": ["Purchase Receipt", "Purchase Invoice", "Sales Order"]},
			{"label": _("Payment"), "items": ["Payment Entry", "Journal Entry", "Payment Request"]},
			{
				"label": _("Reference"),
				"items": ["Supplier Quotation", "Project", "Auto Repeat"],
			},
			{
				"label": _("Manufacturing"),
				"items": ["Material Request", "BOM", "Production Plan", "Blanket Order"],
=======
		},
		"transactions": [
			{"label": _("Related"), "items": ["Purchase Receipt", "Purchase Invoice"]},
			{"label": _("Payment"), "items": ["Payment Entry", "Journal Entry", "Payment Request"]},
			{
				"label": _("Reference"),
				"items": ["Material Request", "Supplier Quotation", "Project", "Auto Repeat"],
>>>>>>> 7c4cf3e834 (Favicon.svg)
			},
			{
				"label": _("Sub-contracting"),
				"items": ["Subcontracting Order", "Subcontracting Receipt", "Stock Entry"],
			},
<<<<<<< HEAD
=======
			{"label": _("Internal"), "items": ["Sales Order"]},
>>>>>>> 7c4cf3e834 (Favicon.svg)
		],
	}
