from frappe import _
from frappe.widgets.moduleview import add_setup_section

def get_data():
	data = [
		{
			"label": _("Settings"),
			"icon": "icon-wrench",
			"items": [
				{
					"type": "doctype",
					"name": "Global Defaults",
					"label": _("Global Settings"),
					"description": _("Set Default Values like Company, Currency, Current Fiscal Year, etc."),
					"hide_count": True
				}
			]
		},
		{
			"label": _("Printing and Branding"),
			"icon": "icon-print",
			"items": [
				{
					"type": "doctype",
					"name": "Letter Head",
					"description": _("Letter Heads for print templates.")
				},
				{
					"type": "doctype",
					"name": "Print Heading",
					"description": _("Titles for print templates e.g. Proforma Invoice.")
				},
				{
					"type": "doctype",
					"name": "Address Template",
					"description": _("Country wise default Address Templates")
				},
				{
					"type": "doctype",
					"name": "Terms and Conditions",
					"description": _("Standard contract terms for Sales or Purchase.")
				},
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
				{
					"type": "doctype",
					"name": "SMS Settings",
					"description": _("Setup SMS gateway settings")
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

	for module, label, icon in (
		("accounts", _("Accounts"), "icon-money"),
		("stock", _("Stock"), "icon-truck"),
		("selling", _("Selling"), "icon-tag"),
		("buying", _("Buying"), "icon-shopping-cart"),
		("hr", _("Human Resources"), "icon-group"),
		("support", _("Support"), "icon-phone")):

		add_setup_section(data, "erpnext", module, label, icon)

	return data
