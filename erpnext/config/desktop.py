# coding=utf-8

from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		# Modules
		{
			"module_name": "Accounting",
			"category": "Modules",
			"label": _("Accounting"),
			"color": "#3498db",
			"icon": "octicon octicon-repo",
			"type": "module",
			"hidden": 1,
			"description": "Accounts, Billing, Payments, Cost Center and Budgeting."
		},
		{
			"module_name": "Selling",
			"category": "Modules",
			"label": _("Selling"),
			"color": "#1abc9c",
			"icon": "octicon octicon-tag",
			"type": "module",
			"hidden": 1,
			"description": "All things Sales, Customer and Products."
		},
		{
			"module_name": "Buying",
			"category": "Modules",
			"label": _("Buying"),
			"color": "#c0392b",
			"icon": "octicon octicon-briefcase",
			"type": "module",
			"hidden": 1,
			"description": "Purchasing, Suppliers and Products."
		},
		{
			"module_name": "Stock",
			"category": "Modules",
			"label": _("Stock"),
			"color": "#f39c12",
			"icon": "octicon octicon-package",
			"type": "module",
			"hidden": 1,
			"description": "Track Stock Transactions, Reports, and Serialized Items and Batches."
		},
		{
			"module_name": "Assets",
			"category": "Modules",
			"label": _("Assets"),
			"color": "#4286f4",
			"icon": "octicon octicon-database",
			"hidden": 1,
			"type": "module",
			"description": "Asset Maintainance and Tools."
		},
		{
			"module_name": "Projects",
			"category": "Modules",
			"label": _("Projects"),
			"color": "#8e44ad",
			"icon": "octicon octicon-rocket",
			"type": "module",
			"hidden": 1,
			"description": "Updates, Timesheets and Activities."
		},
		{
			"module_name": "CRM",
			"category": "Modules",
			"label": _("CRM"),
			"color": "#EF4DB6",
			"icon": "octicon octicon-broadcast",
			"type": "module",
			"hidden": 1,
			"description": "Everything in your sales pipeline, from Leads to Customers, to Support."
		},
		{
			"module_name": "HR",
			"category": "Modules",
			"label": _("Human Resources"),
			"color": "#2ecc71",
			"icon": "octicon octicon-organization",
			"type": "module",
			"hidden": 1,
			"description": "Employee Lifecycle, Payroll, Shifts and Leaves."
		},
		{
			"module_name": "Quality Management",
			"category": "Modules",
			"label": _("Quality"),
			"color": "#1abc9c",
			"icon": "fa fa-check-square-o",
			"type": "module",
			"hidden": 1,
			"description": "Volunteers, Memberships, Grants and Chapters."
		},


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
		{
			"module_name": "Settings",
			"category": "Administration",
			"label": _("Settings"),
			"color": "#bdc3c7",
			"reverse": 1,
			"icon": "octicon octicon-settings",
			"type": "module",
			"hidden": 1,
			"description": "Global settings for all modules in ERPNext, with Email Digest and SMS."
		},
	]
