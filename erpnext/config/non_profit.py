from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Chapter"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "doctype",
					"name": "Chapter",
					"description": _("Chapter information."),
				},
				{
					"type": "doctype",
					"name": "Chapter Message",
					"description": _("Chapter Message."),
				},
			]
		},
		{
			"label": _("Membership"),
			"items": [
				{
					"type": "doctype",
					"name": "Member",
					"description": _("Member information."),
				},
				{
					"type": "doctype",
					"name": "Membership",
					"description": _("Memebership Details"),
				},
				{
					"type": "doctype",
					"name": "Membership Type",
					"description": _("Memebership Type Details"),
				},
			]
		}
	]
