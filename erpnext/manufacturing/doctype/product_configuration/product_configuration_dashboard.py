from frappe import _


def get_data():
	return {
		"internal_links": {"BOM": "bom"},
		"transactions": [{"label": _("Manufacture"), "items": ["BOM"]}],
	}
