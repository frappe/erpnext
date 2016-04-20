from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "Item",
			"_doctype": "Item",
			"color": "#f39c12",
			"icon": "octicon octicon-package",
			"type": "link",
			"link": "List/Item"
		},
		{
			"module_name": "Customer",
			"_doctype": "Customer",
			"color": "#1abc9c",
			"icon": "octicon octicon-tag",
			"type": "link",
			"link": "List/Customer"
		},
		{
			"module_name": "Supplier",
			"_doctype": "Supplier",
			"color": "#c0392b",
			"icon": "octicon octicon-briefcase",
			"type": "link",
			"link": "List/Supplier"
		},
		{
			"_doctype": "Employee",
			"module_name": "Employee",
			"color": "#2ecc71",
			"icon": "octicon octicon-organization",
			"type": "link",
			"link": "List/Employee"
		},
		{
			"module_name": "Project",
			"_doctype": "Project",
			"color": "#8e44ad",
			"icon": "octicon octicon-rocket",
			"type": "link",
			"link": "List/Project"
		},
		{
			"module_name": "Issue",
			"color": "#2c3e50",
			"icon": "octicon octicon-issue-opened",
			"_doctype": "Issue",
			"type": "link",
			"link": "List/Issue"
		},
		{
			"module_name": "Lead",
			"icon": "octicon octicon-broadcast",
			"type": "module",
			"_doctype": "Lead",
			"type": "link",
			"link": "List/Lead"
		},
		{
			"module_name": "Profit and Loss Statment",
			"_doctype": "Account",
			"color": "#3498db",
			"icon": "octicon octicon-repo",
			"type": "link",
			"link": "query-report/Profit and Loss Statement"
		},

		# old
		{
			"module_name": "Accounts",
			"color": "#3498db",
			"icon": "octicon octicon-repo",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "Stock",
			"color": "#f39c12",
			"icon": "icon-truck",
			"icon": "octicon octicon-package",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "CRM",
			"color": "#EF4DB6",
			"icon": "octicon octicon-broadcast",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "Selling",
			"color": "#1abc9c",
			"icon": "icon-tag",
			"icon": "octicon octicon-tag",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "Buying",
			"color": "#c0392b",
			"icon": "icon-shopping-cart",
			"icon": "octicon octicon-briefcase",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "HR",
			"color": "#2ecc71",
			"icon": "icon-group",
			"icon": "octicon octicon-organization",
			"label": _("Human Resources"),
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "Manufacturing",
			"color": "#7f8c8d",
			"icon": "icon-cogs",
			"icon": "octicon octicon-tools",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "POS",
			"color": "#589494",
			"icon": "icon-th",
			"icon": "octicon octicon-credit-card",
			"type": "page",
			"link": "pos",
			"label": _("POS"),
			"hidden": 1
		},
		{
			"module_name": "Projects",
			"color": "#8e44ad",
			"icon": "icon-puzzle-piece",
			"icon": "octicon octicon-rocket",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "Support",
			"color": "#2c3e50",
			"icon": "icon-phone",
			"icon": "octicon octicon-issue-opened",
			"type": "module",
			"hidden": 1
		},
		{
			"module_name": "Learn",
			"color": "#FF888B",
			"icon": "octicon octicon-device-camera-video",
			"type": "module",
			"is_help": True,
			"label": _("Learn"),
			"hidden": 1
		}
	]
