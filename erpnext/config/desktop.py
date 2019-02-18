# coding=utf-8

from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		# Modules
		{
			"module_name": "Getting Started",
			"category": "Modules",
			"label": _("Getting Started"),
			"color": "#1abc9c",
			"icon": "fa fa-check-square-o",
			"type": "module",
			"hidden": 1,
			"description": "Dive into the basics for your organisation's needs."
		},
		{
			"module_name": "Accounting",
			"category": "Modules",
			"label": _("Accounting"),
			"color": "#3498db",
			"icon": "octicon octicon-repo",
			"type": "module",
			"hidden": 1,
			"description": "Accounts, billing, payments, cost center and budgeting."
		},
		{
			"module_name": "Selling",
			"category": "Modules",
			"label": _("Selling"),
			"color": "#1abc9c",
			"icon": "octicon octicon-tag",
			"type": "module",
			"hidden": 1,
			"description": "Sales orders, quotations, customers and items."
		},
		{
			"module_name": "Buying",
			"category": "Modules",
			"label": _("Buying"),
			"color": "#c0392b",
			"icon": "octicon octicon-briefcase",
			"type": "module",
			"hidden": 1,
			"description": "Purchasing, suppliers, material requests, and items."
		},
		{
			"module_name": "Stock",
			"category": "Modules",
			"label": _("Stock"),
			"color": "#f39c12",
			"icon": "octicon octicon-package",
			"type": "module",
			"hidden": 1,
			"description": "Stock transactions, reports, serial numbers and batches."
		},
		{
			"module_name": "Assets",
			"category": "Modules",
			"label": _("Assets"),
			"color": "#4286f4",
			"icon": "octicon octicon-database",
			"hidden": 1,
			"type": "module",
			"description": "Asset movement, maintainance and tools."
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
			"description": "Sales pipeline, leads, opportunities and customers."
		},
		{
			"module_name": "Help Desk",
			"category": "Modules",
			"label": _("Help Desk"),
			"color": "#1abc9c",
			"icon": "fa fa-check-square-o",
			"type": "module",
			"hidden": 1,
			"description": "User interactions, support issues and knowledge base."
		},
		{
			"module_name": "HR",
			"category": "Modules",
			"label": _("Human Resources"),
			"color": "#2ecc71",
			"icon": "octicon octicon-organization",
			"type": "module",
			"hidden": 1,
			"description": "Employees, attendance, payroll, leaves and shifts."
		},
		{
			"module_name": "Quality Management",
			"category": "Modules",
			"label": _("Quality"),
			"color": "#1abc9c",
			"icon": "fa fa-check-square-o",
			"type": "module",
			"hidden": 1,
			"description": "Quality goals, procedures, reviews and action."
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
			"description": "BOMS, work orders, operations, and timesheets."
		},
		{
			"module_name": "Retail",
			"category": "Domains",
			"label": _("Retail"),
			"color": "#7f8c8d",
			"icon": "octicon octicon-credit-card",
			"type": "module",
			"hidden": 1,
			"description": "Point of Sale and cashier closing."
		},
		{
			"module_name": "Education",
			"category": "Domains",
			"label": _("Education"),
			"color": "#428B46",
			"icon": "octicon octicon-mortar-board",
			"type": "module",
			"hidden": 1,
			"description": "Student admissions, fees, courses and scores."
		},

		{
			"module_name": "Healthcare",
			"category": "Domains",
			"label": _("Healthcare"),
			"color": "#FF888B",
			"icon": "fa fa-heartbeat",
			"type": "module",
			"hidden": 1,
			"description": "Patient appointments, procedures and tests."
		},
		{
			"module_name": "Agriculture",
			"category": "Domains",
			"label": _("Agriculture"),
			"color": "#8BC34A",
			"icon": "octicon octicon-globe",
			"type": "module",
			"hidden": 1,
			"description": "Crop cycles, land areas, soil and plant analysis."
		},
		{
			"module_name": "Hotels",
			"category": "Domains",
			"label": _("Hotels"),
			"color": "#EA81E8",
			"icon": "fa fa-bed",
			"type": "module",
			"hidden": 1,
			"description": "Hotel rooms, pricing, reservation and amenities."
		},

		{
			"module_name": "Non Profit",
			"category": "Domains",
			"label": _("Non Profit"),
			"color": "#DE2B37",
			"icon": "octicon octicon-heart",
			"type": "module",
			"hidden": 1,
			"description": "Volunteers, memberships, grants and chapters."
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
			"description": "Publish items to other ERPNext users."
		},
	]
