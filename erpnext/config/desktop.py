from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "Accounts",
			"color": "#3498db",
			"icon": "octicon octicon-repo",
			"type": "module"
		},
		{
			"module_name": "CRM",
			"color": "#EF4DB6",
			"icon": "octicon octicon-broadcast",
			"type": "module"
		},
		{
			"module_name": "Selling",
			"color": "#1abc9c",
			"icon": "icon-tag",
			"icon": "octicon octicon-tag",
			"type": "module"
		},
		{
			"module_name": "Buying",
			"color": "#c0392b",
			"icon": "icon-shopping-cart",
			"icon": "octicon octicon-briefcase",
			"type": "module"
		},
		{
			"module_name": "HR",
			"color": "#2ecc71",
			"icon": "icon-group",
			"icon": "octicon octicon-organization",
			"label": _("Human Resources"),
			"type": "module"
		},
		{
			"module_name": "Manufacturing",
			"color": "#7f8c8d",
			"icon": "icon-cogs",
			"icon": "octicon octicon-tools",
			"type": "module"
		},
		{
			"module_name": "POS",
			"color": "#589494",
			"icon": "icon-th",
			"icon": "octicon octicon-credit-card",
			"type": "page",
			"link": "pos",
			"label": _("POS")
		},
		{
			"module_name": "Projects",
			"color": "#8e44ad",
			"icon": "icon-puzzle-piece",
			"icon": "octicon octicon-rocket",
			"type": "module"
		},
		{
			"module_name": "Stock",
			"color": "#f39c12",
			"icon": "icon-truck",
			"icon": "octicon octicon-package",
			"type": "module"
		},
		{
			"module_name": "Support",
			"color": "#2c3e50",
			"icon": "icon-phone",
			"icon": "octicon octicon-issue-opened",
			"type": "module"
		},
		{
			"module_name": "Learn",
			"color": "#FF888B",
			"icon": "octicon octicon-device-camera-video",
			"type": "module",
			"is_help": True,
			"label": _("Learn")
		}
	]
