from frappe import _

def get_data():
	return [
		{
			"label": _("Documents"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Lead",
					"description": _("Database of potential customers."),
				},
				{
					"type": "doctype",
					"name": "Customer",
					"description": _("Customer database."),
				},
				{
					"type": "doctype",
					"name": "Opportunity",
					"description": _("Potential opportunities for selling."),
				},
				{
					"type": "doctype",
					"name": "Contact",
					"description": _("All Contacts."),
				},
				{
					"type": "doctype",
					"name": "Newsletter",
					"description": _("Newsletters to contacts, leads."),
				},
				{
					"type": "doctype",
					"name": "Communication",
					"description": _("Record of all communications of type email, phone, chat, visit, etc."),
				},
			]
		},
		{
			"label": _("Tools"),
			"icon": "icon-wrench",
			"items": [
				{
					"type": "doctype",
					"name": "SMS Center",
					"description":_("Send mass SMS to your contacts"),
				},
				{
					"type": "doctype",
					"name": "SMS Log",
					"description":_("Logs for maintaining sms delivery status"),
				}
			]
		},
		{
			"label": _("Setup"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Campaign",
					"description": _("Sales campaigns."),
				},
				{
					"type": "page",
					"label": _("Customer Group"),
					"name": "Sales Browser",
					"icon": "icon-sitemap",
					"link": "Sales Browser/Customer Group",
					"description": _("Manage Customer Group Tree."),
					"doctype": "Customer Group",
				},
				{
					"type": "page",
					"label": _("Territory"),
					"name": "Sales Browser",
					"icon": "icon-sitemap",
					"link": "Sales Browser/Territory",
					"description": _("Manage Territory Tree."),
					"doctype": "Territory",
				},
				{
					"type": "page",
					"label": _("Sales Person"),
					"name": "Sales Browser",
					"icon": "icon-sitemap",
					"link": "Sales Browser/Sales Person",
					"description": _("Manage Sales Person Tree."),
					"doctype": "Sales Person",
				},
				{
					"type": "doctype",
					"name": "Newsletter List",
					"description": _("Newsletter Mailing List"),
				},
				{
					"type": "doctype",
					"name": "SMS Settings",
					"description": _("Setup SMS gateway settings")
				},
			]
		},
		{
			"label": _("Main Reports"),
			"icon": "icon-table",
			"items": [
				{
					"type": "page",
					"name": "sales-funnel",
					"label": _("Sales Funnel"),
					"icon": "icon-bar-chart",
				},
			]
		},
		{
			"label": _("Standard Reports"),
			"icon": "icon-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Lead Details",
					"doctype": "Lead"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Customer Addresses and Contacts",
					"doctype": "Contact"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Customers Not Buying Since Long Time",
					"doctype": "Sales Order"
				},
			]
		},
		{
			"label": _("Help"),
			"items": [
				{
					"type": "help",
					"label": _("Lead to Quotation"),
					"youtube_id": "TxYX4r4JAKA"
				},
			]
		},
	]
