from frappe import _
from frappe.widgets.moduleview import add_setup_section

data = [
	{
		"label": _("Tools"),
		"icon": "icon-wrench",
		"items": [
			{
				"type": "doctype",
				"name": "Global Defaults",
				"label": _("Global Settings"),
				"description": _("Set the Date & Number Formats, Default Currency, Current Fiscal Year, etc."),
				"hide_count": True
			}
		]
	},
	{
		"label": _("Customize"),
		"icon": "icon-glass",
		"items": [
			{
				"type": "doctype",
				"name": "Features Setup",
				"description": _("Show / Hide features like Serial Nos, POS etc.")
			},
			{
				"type": "doctype",
				"name": "Authorization Rule",
				"description": _("Create rules to restrict transactions based on values.")
			},
			{
				"type": "doctype",
				"name": "Notification Control",
				"label": _("Email Notifications"),
				"description": _("Automatically compose message on submission of transactions.")
			}
		]
	},
	{
		"label": _("Email"),
		"icon": "icon-envelope",
		"items": [
			{
				"type": "doctype",
				"name": "Email Digest",
				"description": _("Create and manage daily, weekly and monthly email digests.")
			},
			{
				"type": "doctype",
				"name": "Support Email Settings",
				"description": _("Setup incoming server for support email id. (e.g. support@example.com)")
			},
			{
				"type": "doctype",
				"name": "Sales Email Settings",
				"description": _("Setup incoming server for sales email id. (e.g. sales@example.com)")
			},
			{
				"type": "doctype",
				"name": "Jobs Email Settings",
				"description": _("Setup incoming server for jobs email id. (e.g. jobs@example.com)")
			},
		]
	},
	{
		"label": _("Masters"),
		"icon": "icon-star",
		"items": [
			{
				"type": "doctype",
				"name": "Company",
				"description": _("Company (not Customer or Supplier) master.")
			},
			{
				"type": "doctype",
				"name": "Item",
				"description": _("Item master.")
			},
			{
				"type": "doctype",
				"name": "Customer",
				"description": _("Customer master.")
			},
			{
				"type": "doctype",
				"name": "Supplier",
				"description": _("Supplier master.")
			},
			{
				"type": "doctype",
				"name": "Contact",
				"description": _("Contact master.")
			},
			{
				"type": "doctype",
				"name": "Address",
				"description": _("Address master.")
			},
		]
	},
]

def get_data():
	out = list(data)
	
	for module, label, icon in (
		("accounts", _("Accounts"), "icon-money"),
		("stock", _("Stock"), "icon-truck"),
		("selling", _("Selling"), "icon-tag"),
		("buying", _("Buying"), "icon-shopping-cart"),
		("hr", _("Human Resources"), "icon-group"),
		("support", _("Support"), "icon-phone")):
		
		add_setup_section(out, "erpnext", module, label, icon)

	return out