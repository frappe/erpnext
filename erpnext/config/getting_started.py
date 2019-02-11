from __future__ import unicode_literals
from frappe import _

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
					"name": "Journal Entry",
					"description": _("Accounting journal entries."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Opening Invoice Creation Tool",
					"description": _("Create Opening Sales and Purchase Invoices")
				},
			]
		},
		{
			"label": _("Selling"),
			"items": [
				{
					"type": "doctype",
					"name": "Customer",
					"description": _("Customer database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Quotation",
					"description": _("Quotes to Leads or Customers."),
					"onboard": 1,
					"dependencies": ["Item", "Customer"],
				},
				{
					"type": "doctype",
					"name": "Sales Order",
					"description": _("Confirmed orders from Customers."),
					"onboard": 1,
					"dependencies": ["Item", "Customer"],
				},
				{
					"type": "doctype",
					"name": "Sales Partner",
					"description": _("Manage Sales Partners."),
					"dependencies": ["Item"],
				},
				{
					"type": "doctype",
					"name": "Selling Settings",
					"description": _("Default settings for selling transactions."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name":"Terms and Conditions",
					"label": _("Terms and Conditions Template"),
					"description": _("Template of terms or contract."),
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Buying"),
			"items": [
				{
					"type": "doctype",
					"name": "Purchase Order",
					"onboard": 1,
					"dependencies": ["Item", "Supplier"],
					"description": _("Purchase Orders given to Suppliers."),
				},
				{
					"type": "doctype",
					"name": "Material Request",
					"onboard": 1,
					"dependencies": ["Item"],
					"description": _("Request for purchase."),
				},
				{
					"type": "doctype",
					"name": "Request for Quotation",
					"onboard": 1,
					"dependencies": ["Item", "Supplier"],
					"description": _("Request for quotation."),
				},
				{
					"type": "doctype",
					"name": "Supplier Quotation",
					"dependencies": ["Item", "Supplier"],
					"description": _("Quotations received from Suppliers."),
				},
				{
					"type": "doctype",
					"name": "Buying Settings",
					"onboard": 1,
					"description": _("Default settings for buying transactions.")
				},
				{
					"type": "doctype",
					"name": "Purchase Taxes and Charges Template",
					"description": _("Tax template for buying transactions.")
				},
				{
					"type": "doctype",
					"name":"Terms and Conditions",
					"label": _("Terms and Conditions Template"),
					"description": _("Template of terms or contract.")
				},
			]
		},
		{
			"label": _("Stock"),
			"items": [
				{
					"type": "doctype",
					"name": "Stock Entry",
					"onboard": 1,
					"dependencies": ["Item"],
				},
				{
					"type": "doctype",
					"name": "Delivery Note",
					"onboard": 1,
					"dependencies": ["Item", "Customer"],
				},
				{
					"type": "doctype",
					"name": "Purchase Receipt",
					"onboard": 1,
					"dependencies": ["Item", "Supplier"],
				},
				{
					"type": "doctype",
					"name": "Material Request",
					"onboard": 1,
					"dependencies": ["Item"],
				},
				{
					"type": "doctype",
					"name": "Delivery Trip"
				},
			]
		},
		{
			"label": _("Assets"),
			"items": [
				{
					"type": "doctype",
					"name": "Asset",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Location",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Asset Category",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Asset Settings",
				},
				{
					"type": "doctype",
					"name": "Asset Movement",
					"description": _("Transfer an asset from one warehouse to another")
				},
			]
		},
		{
			"label": _("Projects"),
			"items": [
				{
					"type": "doctype",
					"name": "Project",
					"description": _("Project master."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Task",
					"route": "List/Task",
					"description": _("Project activity / task."),
					"onboard": 1,
				},
				{
					"type": "report",
					"route": "List/Task/Gantt",
					"doctype": "Task",
					"name": "Gantt Chart",
					"description": _("Gantt chart of all tasks."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Project Update",
					"description": _("Project Update."),
					"dependencies": ["Project"],
				},
				{
					"type": "doctype",
					"name": "Timesheet",
					"description": _("Timesheet for tasks."),
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
					"name": "Customer",
					"description": _("Customer database."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Contact",
					"description": _("All Contacts."),
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
				{
					"type": "doctype",
					"label": _("Sales Person"),
					"name": "Sales Person",
					"icon": "fa fa-sitemap",
					"link": "Tree/Sales Person",
					"description": _("Manage Sales Person Tree."),
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Help Desk"),
			"items": [
				{
					"type": "doctype",
					"name": "Issue",
					"description": _("Support queries from customers."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Communication",
					"description": _("Communication log."),
					"onboard": 1,
				},
				{
					"type": "page",
					"name": "support-analytics",
					"label": _("Support Analytics"),
					"icon": "fa fa-bar-chart"
				},
				{
					"type": "report",
					"name": "Minutes to First Response for Issues",
					"doctype": "Issue",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Support Hours",
					"doctype": "Issue",
					"is_query_report": True
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
					"name": "Attendance",
					"onboard": 1,
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Salary Structure",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Salary Structure Assignment",
					"onboard": 1,
					"dependencies": ["Salary Structure", "Employee"],
				},
				{
					"type": "doctype",
					"name": "Salary Slip",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Payroll Entry",
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Quality"),
			"items": [
				{
					"type": "doctype",
					"name": "Quality Goal",
					"description":_("Quality Goal."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Quality Procedure",
					"description":_("Quality Procedure."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Quality Procedure",
					"icon": "fa fa-sitemap",
					"label": _("Tree of Procedures"),
					"route": "Tree/Quality Procedure",
					"description": _("Tree of Quality Procedures."),
				},
				{
					"type": "doctype",
					"name": "Quality Review",
					"description":_("Quality Review"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Quality Action",
					"description":_("Quality Action"),
				}
			]
		},
		{
			"label": _("Manufacturing"),
			"items": [
				{
					"type": "doctype",
					"name": "Work Order",
					"description": _("Orders released for production."),
					"onboard": 1,
					"dependencies": ["Item", "BOM"]
				},
				{
					"type": "doctype",
					"name": "Production Plan",
					"description": _("Generate Material Requests (MRP) and Work Orders."),
					"onboard": 1,
					"dependencies": ["Item", "BOM"]
				},
				{
					"type": "doctype",
					"name": "Stock Entry",
					"onboard": 1,
					"dependencies": ["Item"]
				},
				{
					"type": "doctype",
					"name": "Timesheet",
					"description": _("Time Sheet for manufacturing."),
					"onboard": 1,
					"dependencies": ["Activity Type"]
				},
				{
					"type": "doctype",
					"name": "Job Card"
				},
				{
					"type": "doctype",
					"name": "Item",
					"description": _("All Products or Services."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "BOM",
					"description": _("Bill of Materials (BOM)"),
					"label": _("Bill of Materials"),
					"onboard": 1,
					"dependencies": ["Item"]
				},
			]
		},
		{
			"label": _("Retail"),
			"items": [
				{
					"type": "doctype",
					"name": "POS Profile",
					"label": _("Point-of-Sale Profile"),
					"description": _("Setup default values for POS Invoices"),
					"onboard": 1,
				},
				{
					"type": "page",
					"name": "pos",
					"label": _("POS"),
					"description": _("Point of Sale"),
					"onboard": 1,
					"dependencies": ["POS Profile"]
				},
				{
					"type": "doctype",
					"name": "Cashier Closing",
					"description": _("Cashier Closing"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "POS Settings",
					"description": _("Setup mode of POS (Online / Offline)"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Loyalty Program",
					"label": _("Loyalty Program"),
					"description": _("To make Customer based incentive schemes.")
				},
				{
					"type": "doctype",
					"name": "Loyalty Point Entry",
					"label": _("Loyalty Point Entry"),
					"description": _("To view logs of Loyalty Points assigned to a Customer.")
				}
			]
		},
		{
			"label": _("Education"),
			"items": [
				{
					"type": "doctype",
					"name": "Student",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Guardian",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Student Group",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Student Attendance",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Fees",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Program Enrollment Tool"
				},
				{
					"type": "doctype",
					"name": "Course Scheduling Tool"
				},
				{
					"type": "doctype",
					"name": "Fee Schedule"
				},
			]
		},
		{
			"label": _("Healthcare"),
			"items": [
				{
					"type": "doctype",
					"name": "Patient Appointment",
					"label": _("Patient Appointment"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Patient Encounter",
					"label": _("Patient Encounter"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Vital Signs",
					"label": _("Vital Signs"),
					"description": _("Record Patient Vitals"),
					"onboard": 1,
				},
				{
					"type": "page",
					"name": "medical_record",
					"label": _("Patient Medical Record"),
					"onboard": 1,
				},
				{
					"type": "page",
					"name": "appointment-analytic",
					"label": _("Appointment Analytics"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Clinical Procedure",
					"label": _("Clinical Procedure"),
				},
				{
					"type": "doctype",
					"name": "Inpatient Record",
					"label": _("Inpatient Record"),
				}
			]
		},
		{
			"label": _("Agriculture"),
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
					"name": "Disease",
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