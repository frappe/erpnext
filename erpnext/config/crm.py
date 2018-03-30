from frappe import _

def get_data():
	return [
		{
			"label": _("Sales Pipeline"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "doctype",
					"name": "Lead",
					"description": _("Database of potential customers."),
				},
				{
					"type": "doctype",
					"name": "Opportunity",
					"description": _("Potential opportunities for selling."),
				},
				{
					"type": "doctype",
					"name": "Customer",
					"description": _("Customer database."),
				},
				{
					"type": "doctype",
					"name": "Contact",
					"description": _("All Contacts."),
				},
			]
		},
		{
			"label": _("Reports"),
			"icon": "fa fa-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Lead Details",
					"doctype": "Lead"
				},
				{
					"type": "page",
					"name": "sales-funnel",
					"label": _("Sales Funnel"),
					"icon": "fa fa-bar-chart",
				},
				{
					"type": "report",
					"name": "Prospects Engaged But Not Converted",
					"doctype": "Lead",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Minutes to First Response for Opportunity",
					"doctype": "Opportunity",
					"is_query_report": True
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Customer Addresses And Contacts",
					"doctype": "Contact"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Inactive Customers",
					"doctype": "Sales Order"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Campaign Efficiency",
					"doctype": "Lead"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Lead Owner Efficiency",
					"doctype": "Lead"
				}
			]
		},
		{
			"label": _("Communication"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "doctype",
					"name": "Communication",
					"description": _("Record of all communications of type email, phone, chat, visit, etc."),
				},
			]
		},
		{
			"label": _("Setup"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Campaign",
					"description": _("Sales campaigns."),
				},
				{
					"type": "doctype",
					"label": _("Customer Group"),
					"name": "Customer Group",
					"icon": "fa fa-sitemap",
					"link": "Tree/Customer Group",
					"description": _("Manage Customer Group Tree."),
				},
				{
					"type": "doctype",
					"label": _("Territory"),
					"name": "Territory",
					"icon": "fa fa-sitemap",
					"link": "Tree/Territory",
					"description": _("Manage Territory Tree."),
				},
				{
					"type": "doctype",
					"label": _("Sales Person"),
					"name": "Sales Person",
					"icon": "fa fa-sitemap",
					"link": "Tree/Sales Person",
					"description": _("Manage Sales Person Tree."),
				},
				{
					"type": "doctype",
					"name": "Lead Source",
					"description": _("Track Leads by Lead Source.")
				},
			]
		},
		{
			"label": _("SMS"),
			"icon": "fa fa-wrench",
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
				},
				{
					"type": "doctype",
					"name": "SMS Settings",
					"description": _("Setup SMS gateway settings")
				}
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
				{
					"type": "help",
					"label": _("Newsletters"),
					"youtube_id": "muLKsCrrDRo"
				},
			]
		},
	]
