from __future__ import unicode_literals
from frappe import _

def get_data():
    return [
        {
            "label": _("Goal and Procedure"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Quality Goal",
                    "description":_("Quality Goal."),
                },
                {
                    "type": "doctype",
                    "name": "Quality Procedure",
                    "description":_("Quality Procedure."),
                },
                {
					"type": "doctype",
					"name": "Quality Procedure",
					"icon": "fa fa-sitemap",
					"label": _("Tree of Procedures"),
					"route": "Tree/Quality Procedure",
					"description": _("Tree of Quality Procedures."),
				},
            ]
        },
        {
            "label": _("Review and Action"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Quality Review",
                    "description":_("Quality Review"),
                },
                {
                    "type": "doctype",
                    "name": "Quality Action",
                    "description":_("Quality Action"),
                }
            ]
        },
        {
            "label": _("Meeting"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Quality Meeting",
                    "description":_("Quality Meeting"),
                }
            ]
        },
        {
            "label": _("Feedback"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Customer Feedback",
                    "description":_("Customer Feedback"),
                },
                {
                    "type": "doctype",
                    "name": "Customer Feedback Template",
                    "description":_("Customer Feedback Template"),
                }
            ]
        },
    ]