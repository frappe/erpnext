from __future__ import unicode_literals
from frappe import _
from frappe.desk.moduleview import add_setup_section

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
			"label": _("Printing"),
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
			"label": _("Help"),
			"items": [
				{
					"type": "help",
					"name": _("Data Import and Export"),
					"youtube_id": "6wiriRKPhmg"
				},
				{
					"type": "help",
					"label": _("Setting up Email"),
					"youtube_id": "YFYe0DrB95o"
				},
				{
					"type": "help",
					"label": _("Printing and Branding"),
					"youtube_id": "cKZHcx1znMc"
				},
				{
					"type": "help",
					"label": _("Users and Permissions"),
					"youtube_id": "fnBoRhBrwR4"
				},
				{
					"type": "help",
					"label": _("Workflow"),
					"youtube_id": "yObJUg9FxFs"
				},
			]
		},
		{
			"label": _("Customize"),
			"icon": "icon-glass",
			"items": [
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
					"name": "SMS Settings",
					"description": _("Setup SMS gateway settings")
				},
			]
		}
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
