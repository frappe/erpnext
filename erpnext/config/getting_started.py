from __future__ import unicode_literals
import frappe
from frappe import _

active_domains = frappe.get_active_domains()

def get_data():
	return [
		{
			"label": _("Accounting"),
			"items": [
				{
					"type": "doctype",
					"name": "Item",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Customer",
					"description": _("Customer database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Supplier",
					"description": _("Supplier database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Company",
					"description": _("Company (not Customer or Supplier) master."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Account",
					"icon": "fa fa-sitemap",
					"label": _("Chart of Accounts"),
					"route": "#Tree/Account",
					"description": _("Tree of financial accounts."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Opening Invoice Creation Tool",
					"description": _("Create Opening Sales and Purchase Invoices"),
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Data Import and Settings"),
			"items": [
				{
					"type": "doctype",
					"name": "Data Import",
					"label": _("Import Data"),
					"icon": "octicon octicon-cloud-upload",
					"description": _("Import Data from CSV / Excel files."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Letter Head",
					"description": _("Letter Heads for print templates."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Email Account",
					"description": _("Add / Manage Email Accounts."),
					"onboard": 1,
				},

			]
		},
		{
			"label": _("Stock"),
			"items": [
				{
					"type": "doctype",
					"name": "Warehouse",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Brand",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "UOM",
					"label": _("Unit of Measure") + " (UOM)",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Stock Reconciliation",
					"onboard": 1,
				},
			]
		},
		{
			"label": _("CRM"),
			"items": [
				{
					"type": "doctype",
					"name": "Lead",
					"description": _("Database of potential customers."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Opportunity",
					"description": _("Potential opportunities for selling."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"label": _("Customer Group"),
					"name": "Customer Group",
					"icon": "fa fa-sitemap",
					"link": "Tree/Customer Group",
					"description": _("Manage Customer Group Tree."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"label": _("Territory"),
					"name": "Territory",
					"icon": "fa fa-sitemap",
					"link": "Tree/Territory",
					"description": _("Manage Territory Tree."),
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Human Resources"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Employee Attendance Tool",
					"hide_count": True,
					"onboard": 1,
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Salary Structure",
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Education"),
			"condition": "Education" in active_domains,
			"items": [
				{
					"type": "doctype",
					"name": "Student",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Course",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Student Group",
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Healthcare"),
			"condition": "Healthcare" in active_domains,
			"items": [
				{
					"type": "doctype",
					"name": "Patient Appointment",
					"label": _("Patient Appointment"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Clinical Procedure",
					"label": _("Clinical Procedure"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Inpatient Record",
					"label": _("Inpatient Record"),
					"onboard": 1,
				}
			]
		},
		{
			"label": _("Agriculture"),
			"condition": "Agriculture" in active_domains,
			"items": [
				{
					"type": "doctype",
					"name": "Crop",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Crop Cycle",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Location",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Fertilizer",
					"onboard": 1,
				}
			]
		},
		{
			"label": _("Non Profit"),
			"condition": "Non Profit" in active_domains,
			"items": [
				{
					"type": "doctype",
					"name": "Member",
					"description": _("Member information."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Volunteer",
					"description": _("Volunteer information."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Chapter",
					"description": _("Chapter information."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Donor",
					"description": _("Donor information."),
					"onboard": 1,
				},
			]
		}
	]