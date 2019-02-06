# coding=utf-8

from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		# Category: "Domains"
		{
			"module_name": "Manufacturing",
			"category": "Domains",
			"label": _("Manufacturing"),
			"color": "#7f8c8d",
			"icon": "octicon octicon-tools",
			"type": "module",
			"hidden": 1,
			"description": "Streamline your production with BOMS, Work Orders and Timesheets."
		},
		{
			"module_name": "Retail",
			"category": "Domains",
			"label": _("Retail"),
			"color": "#7f8c8d",
			"icon": "octicon octicon-credit-card",
			"type": "module",
			"hidden": 1,
			"description": "Point of Sale, Cashier Closing and Loyalty Programs."
		},
		{
			"module_name": "Education",
			"category": "Domains",
			"label": _("Education"),
			"color": "#428B46",
			"icon": "octicon octicon-mortar-board",
			"type": "module",
			"hidden": 1,
			"description": "Manage Student Admissions, Fees, Subjects and Score Reports."
		},

		{
			"module_name": "Healthcare",
			"category": "Domains",
			"label": _("Healthcare"),
			"color": "#FF888B",
			"icon": "fa fa-heartbeat",
			"type": "module",
			"hidden": 1,
			"description": "Patients appointments, procedures and tests, with diagnosis reports and drug prescriptions."
		},
		{
			"module_name": "Agriculture",
			"category": "Domains",
			"label": _("Agriculture"),
			"color": "#8BC34A",
			"icon": "octicon octicon-globe",
			"type": "module",
			"hidden": 1,
			"description": "Crop Cycles, Land Areas and Soil and Plant Analysis."
		},
		{
			"module_name": "Hotels",
			"category": "Domains",
			"label": _("Hotels"),
			"color": "#EA81E8",
			"icon": "fa fa-bed",
			"type": "module",
			"hidden": 1,
			"description": "Manage Hotel Rooms, Pricing, Reservation and Amenities."
		},

		{
			"module_name": "Non Profit",
			"category": "Domains",
			"label": _("Non Profit"),
			"color": "#DE2B37",
			"icon": "octicon octicon-heart",
			"type": "module",
			"hidden": 1,
			"description": "Make benefiting others easier with Volunteers, Memberships, Grants and Chapters."
		},
		{
			"module_name": "Restaurant",
			"category": "Domains",
			"label": _("Restaurant"),
			"color": "#EA81E8",
			"icon": "fa fa-cutlery",
			"_doctype": "Restaurant",
			"type": "module",
			"link": "List/Restaurant",
			"hidden": 1,
			"description": "Menu, Orders and Table Reservations."
		},


		{
			"module_name": "Learn",
			"category": "Administration",
			"label": _("Learn"),
			"color": "#FF888B",
			"icon": "octicon octicon-device-camera-video",
			"type": "module",
			"is_help": True,
			"description": "Explore Help Articles and Videos."
		},
		{
			"module_name": 'Marketplace',
			"category": "Places",
			"label": _('Marketplace'),
			"icon": "octicon octicon-star",
			"type": 'link',
			"link": '#marketplace/home',
			"color": '#FF4136',
			'standard': 1,
			"description": "Publish items to other ERPNext users and start a conversation."
		},
	]
