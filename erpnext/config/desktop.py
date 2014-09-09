from frappe import _

def get_data():
	return {
		"Accounts": {
			"color": "#3498db",
			"icon": "icon-money",
			"type": "module"
		},
		"Activity": {
			"color": "#e67e22",
			"icon": "icon-play",
			"label": _("Activity"),
			"link": "activity",
			"type": "page"
		},
		"Buying": {
			"color": "#c0392b",
			"icon": "icon-shopping-cart",
			"type": "module"
		},
		"HR": {
			"color": "#2ecc71",
			"icon": "icon-group",
			"label": _("Human Resources"),
			"type": "module"
		},
		"Manufacturing": {
			"color": "#7f8c8d",
			"icon": "icon-cogs",
			"type": "module"
		},
		"Notes": {
			"color": "#95a5a6",
			"doctype": "Note",
			"icon": "icon-file-alt",
			"label": _("Notes"),
			"link": "List/Note",
			"type": "list"
		},
		"POS": {
			"color": "#589494",
			"icon": "icon-th",
			"type": "page",
			"link": "pos"
		},
		"Projects": {
			"color": "#8e44ad",
			"icon": "icon-puzzle-piece",
			"type": "module"
		},
		"Selling": {
			"color": "#1abc9c",
			"icon": "icon-tag",
			"type": "module"
		},
		"Stock": {
			"color": "#f39c12",
			"icon": "icon-truck",
			"type": "module"
		},
		"Support": {
			"color": "#2c3e50",
			"icon": "icon-phone",
			"type": "module"
		}
	}
