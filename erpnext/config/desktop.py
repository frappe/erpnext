from frappe import _

def get_data():
	return {
		"Accounts": {
			"color": "#3498db",
			"icon": "icon-money",
			"type": "module"
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
		},
		"Shopping Cart": {
			"color": "#B7E090",
			"icon": "icon-shopping-cart",
			"label": _("Shopping Cart"),
			"link": "Form/Shopping Cart Settings",
			"type": "module"
		}
	}
