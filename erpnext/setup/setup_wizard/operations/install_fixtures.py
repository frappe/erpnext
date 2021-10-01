# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import json
import os

import frappe
from frappe import _
from frappe.desk.doctype.global_search_settings.global_search_settings import (
	update_global_search_doctypes,
)
from frappe.desk.page.setup_wizard.setup_wizard import make_records
from frappe.utils import cstr, getdate
from frappe.utils.nestedset import rebuild_tree

from erpnext.accounts.doctype.account.account import RootNotEditable
from erpnext.regional.address_template.setup import set_up_address_templates

default_lead_sources = ["Existing Customer", "Reference", "Advertisement",
	"Cold Calling", "Exhibition", "Supplier Reference", "Mass Mailing",
	"Customer's Vendor", "Campaign", "Walk In"]

default_sales_partner_type = ["Channel Partner", "Distributor", "Dealer", "Agent",
	"Retailer", "Implementation Partner", "Reseller"]

def install(country=None):
	records = [
		# domains
		{ 'doctype': 'Domain', 'domain': 'Distribution'},
		{ 'doctype': 'Domain', 'domain': 'Manufacturing'},
		{ 'doctype': 'Domain', 'domain': 'Retail'},
		{ 'doctype': 'Domain', 'domain': 'Services'},
		{ 'doctype': 'Domain', 'domain': 'Education'},
		{ 'doctype': 'Domain', 'domain': 'Healthcare'},
		{ 'doctype': 'Domain', 'domain': 'Agriculture'},
		{ 'doctype': 'Domain', 'domain': 'Non Profit'},

		# ensure at least an empty Address Template exists for this Country
		{'doctype':"Address Template", "country": country},

		# item group
		{'doctype': 'Item Group', 'item_group_name': _('All Item Groups'),
			'is_group': 1, 'parent_item_group': ''},
		{'doctype': 'Item Group', 'item_group_name': _('Products'),
			'is_group': 0, 'parent_item_group': _('All Item Groups'), "show_in_website": 1 },
		{'doctype': 'Item Group', 'item_group_name': _('Raw Material'),
			'is_group': 0, 'parent_item_group': _('All Item Groups') },
		{'doctype': 'Item Group', 'item_group_name': _('Services'),
			'is_group': 0, 'parent_item_group': _('All Item Groups') },
		{'doctype': 'Item Group', 'item_group_name': _('Sub Assemblies'),
			'is_group': 0, 'parent_item_group': _('All Item Groups') },
		{'doctype': 'Item Group', 'item_group_name': _('Consumable'),
			'is_group': 0, 'parent_item_group': _('All Item Groups') },

		# salary component
		{'doctype': 'Salary Component', 'salary_component': _('Income Tax'), 'description': _('Income Tax'), 'type': 'Deduction', 'is_income_tax_component': 1},
		{'doctype': 'Salary Component', 'salary_component': _('Basic'), 'description': _('Basic'), 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': _('Arrear'), 'description': _('Arrear'), 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': _('Leave Encashment'), 'description': _('Leave Encashment'), 'type': 'Earning'},


		# expense claim type
		{'doctype': 'Expense Claim Type', 'name': _('Calls'), 'expense_type': _('Calls')},
		{'doctype': 'Expense Claim Type', 'name': _('Food'), 'expense_type': _('Food')},
		{'doctype': 'Expense Claim Type', 'name': _('Medical'), 'expense_type': _('Medical')},
		{'doctype': 'Expense Claim Type', 'name': _('Others'), 'expense_type': _('Others')},
		{'doctype': 'Expense Claim Type', 'name': _('Travel'), 'expense_type': _('Travel')},

		# leave type
		{'doctype': 'Leave Type', 'leave_type_name': _('Casual Leave'), 'name': _('Casual Leave'),
			'allow_encashment': 1, 'is_carry_forward': 1, 'max_continuous_days_allowed': '3', 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Compensatory Off'), 'name': _('Compensatory Off'),
			'allow_encashment': 0, 'is_carry_forward': 0, 'include_holiday': 1, 'is_compensatory':1 },
		{'doctype': 'Leave Type', 'leave_type_name': _('Sick Leave'), 'name': _('Sick Leave'),
			'allow_encashment': 0, 'is_carry_forward': 0, 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Privilege Leave'), 'name': _('Privilege Leave'),
			'allow_encashment': 0, 'is_carry_forward': 0, 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Leave Without Pay'), 'name': _('Leave Without Pay'),
			'allow_encashment': 0, 'is_carry_forward': 0, 'is_lwp':1, 'include_holiday': 1},

		# Employment Type
		{'doctype': 'Employment Type', 'employee_type_name': _('Full-time')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Part-time')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Probation')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Contract')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Commission')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Piecework')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Intern')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Apprentice')},


		# Stock Entry Type
		{'doctype': 'Stock Entry Type', 'name': 'Material Issue', 'purpose': 'Material Issue'},
		{'doctype': 'Stock Entry Type', 'name': 'Material Receipt', 'purpose': 'Material Receipt'},
		{'doctype': 'Stock Entry Type', 'name': 'Material Transfer', 'purpose': 'Material Transfer'},
		{'doctype': 'Stock Entry Type', 'name': 'Manufacture', 'purpose': 'Manufacture'},
		{'doctype': 'Stock Entry Type', 'name': 'Repack', 'purpose': 'Repack'},
		{'doctype': 'Stock Entry Type', 'name': 'Send to Subcontractor', 'purpose': 'Send to Subcontractor'},
		{'doctype': 'Stock Entry Type', 'name': 'Material Transfer for Manufacture', 'purpose': 'Material Transfer for Manufacture'},
		{'doctype': 'Stock Entry Type', 'name': 'Material Consumption for Manufacture', 'purpose': 'Material Consumption for Manufacture'},

		# Designation
		{'doctype': 'Designation', 'designation_name': _('CEO')},
		{'doctype': 'Designation', 'designation_name': _('Manager')},
		{'doctype': 'Designation', 'designation_name': _('Analyst')},
		{'doctype': 'Designation', 'designation_name': _('Engineer')},
		{'doctype': 'Designation', 'designation_name': _('Accountant')},
		{'doctype': 'Designation', 'designation_name': _('Secretary')},
		{'doctype': 'Designation', 'designation_name': _('Associate')},
		{'doctype': 'Designation', 'designation_name': _('Administrative Officer')},
		{'doctype': 'Designation', 'designation_name': _('Business Development Manager')},
		{'doctype': 'Designation', 'designation_name': _('HR Manager')},
		{'doctype': 'Designation', 'designation_name': _('Project Manager')},
		{'doctype': 'Designation', 'designation_name': _('Head of Marketing and Sales')},
		{'doctype': 'Designation', 'designation_name': _('Software Developer')},
		{'doctype': 'Designation', 'designation_name': _('Designer')},
		{'doctype': 'Designation', 'designation_name': _('Researcher')},

		# territory: with two default territories, one for home country and one named Rest of the World
		{'doctype': 'Territory', 'territory_name': _('All Territories'), 'is_group': 1, 'name': _('All Territories'), 'parent_territory': ''},
		{'doctype': 'Territory', 'territory_name': country.replace("'", ""), 'is_group': 0, 'parent_territory': _('All Territories')},
		{'doctype': 'Territory', 'territory_name': _("Rest Of The World"), 'is_group': 0, 'parent_territory': _('All Territories')},

		# customer group
		{'doctype': 'Customer Group', 'customer_group_name': _('All Customer Groups'), 'is_group': 1, 	'name': _('All Customer Groups'), 'parent_customer_group': ''},
		{'doctype': 'Customer Group', 'customer_group_name': _('Individual'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
		{'doctype': 'Customer Group', 'customer_group_name': _('Commercial'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
		{'doctype': 'Customer Group', 'customer_group_name': _('Non Profit'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
		{'doctype': 'Customer Group', 'customer_group_name': _('Government'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},

		# supplier group
		{'doctype': 'Supplier Group', 'supplier_group_name': _('All Supplier Groups'), 'is_group': 1, 'name': _('All Supplier Groups'), 'parent_supplier_group': ''},
		{'doctype': 'Supplier Group', 'supplier_group_name': _('Services'), 'is_group': 0, 'parent_supplier_group': _('All Supplier Groups')},
		{'doctype': 'Supplier Group', 'supplier_group_name': _('Local'), 'is_group': 0, 'parent_supplier_group': _('All Supplier Groups')},
		{'doctype': 'Supplier Group', 'supplier_group_name': _('Raw Material'), 'is_group': 0, 'parent_supplier_group': _('All Supplier Groups')},
		{'doctype': 'Supplier Group', 'supplier_group_name': _('Electrical'), 'is_group': 0, 'parent_supplier_group': _('All Supplier Groups')},
		{'doctype': 'Supplier Group', 'supplier_group_name': _('Hardware'), 'is_group': 0, 'parent_supplier_group': _('All Supplier Groups')},
		{'doctype': 'Supplier Group', 'supplier_group_name': _('Pharmaceutical'), 'is_group': 0, 'parent_supplier_group': _('All Supplier Groups')},
		{'doctype': 'Supplier Group', 'supplier_group_name': _('Distributor'), 'is_group': 0, 'parent_supplier_group': _('All Supplier Groups')},

		# Sales Person
		{'doctype': 'Sales Person', 'sales_person_name': _('Sales Team'), 'is_group': 1, "parent_sales_person": ""},

		# Mode of Payment
		{'doctype': 'Mode of Payment',
			'mode_of_payment': 'Check' if country=="United States" else _('Cheque'),
			'type': 'Bank'},
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Cash'),
			'type': 'Cash'},
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Credit Card'),
			'type': 'Bank'},
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Wire Transfer'),
			'type': 'Bank'},
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Bank Draft'),
			'type': 'Bank'},

		# Activity Type
		{'doctype': 'Activity Type', 'activity_type': _('Planning')},
		{'doctype': 'Activity Type', 'activity_type': _('Research')},
		{'doctype': 'Activity Type', 'activity_type': _('Proposal Writing')},
		{'doctype': 'Activity Type', 'activity_type': _('Execution')},
		{'doctype': 'Activity Type', 'activity_type': _('Communication')},

		{'doctype': "Item Attribute", "attribute_name": _("Size"), "item_attribute_values": [
			{"attribute_value": _("Extra Small"), "abbr": "XS"},
			{"attribute_value": _("Small"), "abbr": "S"},
			{"attribute_value": _("Medium"), "abbr": "M"},
			{"attribute_value": _("Large"), "abbr": "L"},
			{"attribute_value": _("Extra Large"), "abbr": "XL"}
		]},

		{'doctype': "Item Attribute", "attribute_name": _("Colour"), "item_attribute_values": [
			{"attribute_value": _("Red"), "abbr": "RED"},
			{"attribute_value": _("Green"), "abbr": "GRE"},
			{"attribute_value": _("Blue"), "abbr": "BLU"},
			{"attribute_value": _("Black"), "abbr": "BLA"},
			{"attribute_value": _("White"), "abbr": "WHI"}
		]},

		# Issue Priority
		{'doctype': 'Issue Priority', 'name': _('Low')},
		{'doctype': 'Issue Priority', 'name': _('Medium')},
		{'doctype': 'Issue Priority', 'name': _('High')},

		#Job Applicant Source
		{'doctype': 'Job Applicant Source', 'source_name': _('Website Listing')},
		{'doctype': 'Job Applicant Source', 'source_name': _('Walk In')},
		{'doctype': 'Job Applicant Source', 'source_name': _('Employee Referral')},
		{'doctype': 'Job Applicant Source', 'source_name': _('Campaign')},

		{'doctype': "Email Account", "email_id": "sales@example.com", "append_to": "Opportunity"},
		{'doctype': "Email Account", "email_id": "support@example.com", "append_to": "Issue"},
		{'doctype': "Email Account", "email_id": "jobs@example.com", "append_to": "Job Applicant"},

		{'doctype': "Party Type", "party_type": "Customer", "account_type": "Receivable"},
		{'doctype': "Party Type", "party_type": "Supplier", "account_type": "Payable"},
		{'doctype': "Party Type", "party_type": "Employee", "account_type": "Payable"},
		{'doctype': "Party Type", "party_type": "Member", "account_type": "Receivable"},
		{'doctype': "Party Type", "party_type": "Shareholder", "account_type": "Payable"},
		{'doctype': "Party Type", "party_type": "Student", "account_type": "Receivable"},
		{'doctype': "Party Type", "party_type": "Donor", "account_type": "Receivable"},

		{'doctype': "Opportunity Type", "name": "Hub"},
		{'doctype': "Opportunity Type", "name": _("Sales")},
		{'doctype': "Opportunity Type", "name": _("Support")},
		{'doctype': "Opportunity Type", "name": _("Maintenance")},

		{'doctype': "Project Type", "project_type": "Internal"},
		{'doctype': "Project Type", "project_type": "External"},
		{'doctype': "Project Type", "project_type": "Other"},

		{"doctype": "Offer Term", "offer_term": _("Date of Joining")},
		{"doctype": "Offer Term", "offer_term": _("Annual Salary")},
		{"doctype": "Offer Term", "offer_term": _("Probationary Period")},
		{"doctype": "Offer Term", "offer_term": _("Employee Benefits")},
		{"doctype": "Offer Term", "offer_term": _("Working Hours")},
		{"doctype": "Offer Term", "offer_term": _("Stock Options")},
		{"doctype": "Offer Term", "offer_term": _("Department")},
		{"doctype": "Offer Term", "offer_term": _("Job Description")},
		{"doctype": "Offer Term", "offer_term": _("Responsibilities")},
		{"doctype": "Offer Term", "offer_term": _("Leaves per Year")},
		{"doctype": "Offer Term", "offer_term": _("Notice Period")},
		{"doctype": "Offer Term", "offer_term": _("Incentives")},

		{'doctype': "Print Heading", 'print_heading': _("Credit Note")},
		{'doctype': "Print Heading", 'print_heading': _("Debit Note")},

		# Assessment Group
		{'doctype': 'Assessment Group', 'assessment_group_name': _('All Assessment Groups'),
			'is_group': 1, 'parent_assessment_group': ''},

		# Share Management
		{"doctype": "Share Type", "title": _("Equity")},
		{"doctype": "Share Type", "title": _("Preference")},

		# Market Segments
		{"doctype": "Market Segment", "market_segment": _("Lower Income")},
		{"doctype": "Market Segment", "market_segment": _("Middle Income")},
		{"doctype": "Market Segment", "market_segment": _("Upper Income")},

		# Sales Stages
		{"doctype": "Sales Stage", "stage_name": _("Prospecting")},
		{"doctype": "Sales Stage", "stage_name": _("Qualification")},
		{"doctype": "Sales Stage", "stage_name": _("Needs Analysis")},
		{"doctype": "Sales Stage", "stage_name": _("Value Proposition")},
		{"doctype": "Sales Stage", "stage_name": _("Identifying Decision Makers")},
		{"doctype": "Sales Stage", "stage_name": _("Perception Analysis")},
		{"doctype": "Sales Stage", "stage_name": _("Proposal/Price Quote")},
		{"doctype": "Sales Stage", "stage_name": _("Negotiation/Review")},

		# Warehouse Type
		{'doctype': 'Warehouse Type', 'name': 'Transit'},
	]

	from erpnext.setup.setup_wizard.data.industry_type import get_industry_types
	records += [{"doctype":"Industry Type", "industry": d} for d in get_industry_types()]
	# records += [{"doctype":"Operation", "operation": d} for d in get_operations()]
	records += [{'doctype': 'Lead Source', 'source_name': _(d)} for d in default_lead_sources]

	records += [{'doctype': 'Sales Partner Type', 'sales_partner_type': _(d)} for d in default_sales_partner_type]

	base_path = frappe.get_app_path("erpnext", "hr", "doctype")
	response = frappe.read_file(os.path.join(base_path, "leave_application/leave_application_email_template.html"))

	records += [{'doctype': 'Email Template', 'name': _("Leave Approval Notification"), 'response': response,
		'subject': _("Leave Approval Notification"), 'owner': frappe.session.user}]

	records += [{'doctype': 'Email Template', 'name': _("Leave Status Notification"), 'response': response,
		'subject': _("Leave Status Notification"), 'owner': frappe.session.user}]

	response = frappe.read_file(os.path.join(base_path, "interview/interview_reminder_notification_template.html"))

	records += [{'doctype': 'Email Template', 'name': _('Interview Reminder'), 'response': response,
		'subject': _('Interview Reminder'), 'owner': frappe.session.user}]

	response = frappe.read_file(os.path.join(base_path, "interview/interview_feedback_reminder_template.html"))

	records += [{'doctype': 'Email Template', 'name': _('Interview Feedback Reminder'), 'response': response,
		'subject': _('Interview Feedback Reminder'), 'owner': frappe.session.user}]

	base_path = frappe.get_app_path("erpnext", "stock", "doctype")
	response = frappe.read_file(os.path.join(base_path, "delivery_trip/dispatch_notification_template.html"))

	records += [{'doctype': 'Email Template', 'name': _("Dispatch Notification"), 'response': response,
		'subject': _("Your order is out for delivery!"), 'owner': frappe.session.user}]

	# Records for the Supplier Scorecard
	from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import make_default_records

	make_default_records()
	make_records(records)
	set_up_address_templates(default_country=country)
	set_more_defaults()
	update_global_search_doctypes()

def set_more_defaults():
	# Do more setup stuff that can be done here with no dependencies
	update_selling_defaults()
	update_buying_defaults()
	update_hr_defaults()
	add_uom_data()
	update_item_variant_settings()

def update_selling_defaults():
	selling_settings = frappe.get_doc("Selling Settings")
	selling_settings.set_default_customer_group_and_territory()
	selling_settings.cust_master_name = "Customer Name"
	selling_settings.so_required = "No"
	selling_settings.dn_required = "No"
	selling_settings.allow_multiple_items = 1
	selling_settings.sales_update_frequency = "Each Transaction"
	selling_settings.save()

def update_buying_defaults():
	buying_settings = frappe.get_doc("Buying Settings")
	buying_settings.supp_master_name = "Supplier Name"
	buying_settings.po_required = "No"
	buying_settings.pr_required = "No"
	buying_settings.maintain_same_rate = 1
	buying_settings.allow_multiple_items = 1
	buying_settings.save()

def update_hr_defaults():
	hr_settings = frappe.get_doc("HR Settings")
	hr_settings.emp_created_by = "Naming Series"
	hr_settings.leave_approval_notification_template = _("Leave Approval Notification")
	hr_settings.leave_status_notification_template = _("Leave Status Notification")

	hr_settings.send_interview_reminder = 1
	hr_settings.interview_reminder_template = _("Interview Reminder")
	hr_settings.remind_before = "00:15:00"

	hr_settings.send_interview_feedback_reminder = 1
	hr_settings.feedback_reminder_notification_template = _("Interview Feedback Reminder")

	hr_settings.save()

def update_item_variant_settings():
	# set no copy fields of an item doctype to item variant settings
	doc = frappe.get_doc('Item Variant Settings')
	doc.set_default_fields()
	doc.save()

def add_uom_data():
	# add UOMs
	uoms = json.loads(open(frappe.get_app_path("erpnext", "setup", "setup_wizard", "data", "uom_data.json")).read())
	for d in uoms:
		if not frappe.db.exists('UOM', _(d.get("uom_name"))):
			uom_doc = frappe.get_doc({
				"doctype": "UOM",
				"uom_name": _(d.get("uom_name")),
				"name": _(d.get("uom_name")),
				"must_be_whole_number": d.get("must_be_whole_number")
			}).db_insert()

	# bootstrap uom conversion factors
	uom_conversions = json.loads(open(frappe.get_app_path("erpnext", "setup", "setup_wizard", "data", "uom_conversion_data.json")).read())
	for d in uom_conversions:
		if not frappe.db.exists("UOM Category", _(d.get("category"))):
			frappe.get_doc({
				"doctype": "UOM Category",
				"category_name": _(d.get("category"))
			}).db_insert()

		if not frappe.db.exists("UOM Conversion Factor", {"from_uom": _(d.get("from_uom")), "to_uom": _(d.get("to_uom"))}):
			uom_conversion = frappe.get_doc({
				"doctype": "UOM Conversion Factor",
				"category": _(d.get("category")),
				"from_uom": _(d.get("from_uom")),
				"to_uom": _(d.get("to_uom")),
				"value": d.get("value")
			}).insert(ignore_permissions=True)

def add_market_segments():
	records = [
		# Market Segments
		{"doctype": "Market Segment", "market_segment": _("Lower Income")},
		{"doctype": "Market Segment", "market_segment": _("Middle Income")},
		{"doctype": "Market Segment", "market_segment": _("Upper Income")}
	]

	make_records(records)

def add_sale_stages():
	# Sale Stages
	records = [
		{"doctype": "Sales Stage", "stage_name": _("Prospecting")},
		{"doctype": "Sales Stage", "stage_name": _("Qualification")},
		{"doctype": "Sales Stage", "stage_name": _("Needs Analysis")},
		{"doctype": "Sales Stage", "stage_name": _("Value Proposition")},
		{"doctype": "Sales Stage", "stage_name": _("Identifying Decision Makers")},
		{"doctype": "Sales Stage", "stage_name": _("Perception Analysis")},
		{"doctype": "Sales Stage", "stage_name": _("Proposal/Price Quote")},
		{"doctype": "Sales Stage", "stage_name": _("Negotiation/Review")}
	]
	for sales_stage in records:
		frappe.get_doc(sales_stage).db_insert()

def install_company(args):
	records = [
		# Fiscal Year
		{
			'doctype': "Fiscal Year",
			'year': get_fy_details(args.fy_start_date, args.fy_end_date),
			'year_start_date': args.fy_start_date,
			'year_end_date': args.fy_end_date
		},

		# Company
		{
			"doctype":"Company",
			'company_name': args.company_name,
			'enable_perpetual_inventory': 1,
			'abbr': args.company_abbr,
			'default_currency': args.currency,
			'country': args.country,
			'create_chart_of_accounts_based_on': 'Standard Template',
			'chart_of_accounts': args.chart_of_accounts,
			'domain': args.domain
		}
	]

	make_records(records)


def install_post_company_fixtures(args=None):
	records = [
		# Department
		{'doctype': 'Department', 'department_name': _('All Departments'), 'is_group': 1, 'parent_department': ''},
		{'doctype': 'Department', 'department_name': _('Accounts'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Marketing'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Sales'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Purchase'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Operations'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Production'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Dispatch'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Customer Service'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Human Resources'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Management'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Quality Management'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Research & Development'), 'parent_department': _('All Departments'), 'company': args.company_name},
		{'doctype': 'Department', 'department_name': _('Legal'), 'parent_department': _('All Departments'), 'company': args.company_name},
	]

	# Make root department with NSM updation
	make_records(records[:1])

	frappe.local.flags.ignore_update_nsm = True
	make_records(records[1:])
	frappe.local.flags.ignore_update_nsm = False
	rebuild_tree("Department", "parent_department")


def install_defaults(args=None):
	records = [
		# Price Lists
		{ "doctype": "Price List", "price_list_name": _("Standard Buying"), "enabled": 1, "buying": 1, "selling": 0, "currency": args.currency },
		{ "doctype": "Price List", "price_list_name": _("Standard Selling"), "enabled": 1, "buying": 0, "selling": 1, "currency": args.currency },
	]

	make_records(records)

	# enable default currency
	frappe.db.set_value("Currency", args.get("currency"), "enabled", 1)
	frappe.db.set_value("Stock Settings", None, "email_footer_address", args.get("company_name"))

	set_global_defaults(args)
	set_active_domains(args)
	update_stock_settings()
	update_shopping_cart_settings(args)

	args.update({"set_default": 1})
	create_bank_account(args)

def set_global_defaults(args):
	global_defaults = frappe.get_doc("Global Defaults", "Global Defaults")
	current_fiscal_year = frappe.get_all("Fiscal Year")[0]

	global_defaults.update({
		'current_fiscal_year': current_fiscal_year.name,
		'default_currency': args.get('currency'),
		'default_company':args.get('company_name')	,
		"country": args.get("country"),
	})

	global_defaults.save()

def set_active_domains(args):
	frappe.get_single('Domain Settings').set_active_domains(args.get('domains'))

def update_stock_settings():
	stock_settings = frappe.get_doc("Stock Settings")
	stock_settings.item_naming_by = "Item Code"
	stock_settings.valuation_method = "FIFO"
	stock_settings.default_warehouse = frappe.db.get_value('Warehouse', {'warehouse_name': _('Stores')})
	stock_settings.stock_uom = _("Nos")
	stock_settings.auto_indent = 1
	stock_settings.auto_insert_price_list_rate_if_missing = 1
	stock_settings.automatically_set_serial_nos_based_on_fifo = 1
	stock_settings.set_qty_in_transactions_based_on_serial_no_input = 1
	stock_settings.save()

def create_bank_account(args):
	if not args.get('bank_account'):
		return

	company_name = args.get('company_name')
	bank_account_group =  frappe.db.get_value("Account",
		{"account_type": "Bank", "is_group": 1, "root_type": "Asset",
			"company": company_name})
	if bank_account_group:
		bank_account = frappe.get_doc({
			"doctype": "Account",
			'account_name': args.get('bank_account'),
			'parent_account': bank_account_group,
			'is_group':0,
			'company': company_name,
			"account_type": "Bank",
		})
		try:
			doc = bank_account.insert()

			if args.get('set_default'):
				frappe.db.set_value("Company", args.get('company_name'), "default_bank_account", bank_account.name, update_modified=False)

			return doc

		except RootNotEditable:
			frappe.throw(_("Bank account cannot be named as {0}").format(args.get('bank_account')))
		except frappe.DuplicateEntryError:
			# bank account same as a CoA entry
			pass

def update_shopping_cart_settings(args):
	shopping_cart = frappe.get_doc("Shopping Cart Settings")
	shopping_cart.update({
		"enabled": 1,
		'company': args.company_name,
		'price_list': frappe.db.get_value("Price List", {"selling": 1}),
		'default_customer_group': _("Individual"),
		'quotation_series': "QTN-",
	})
	shopping_cart.update_single(shopping_cart.get_valid_dict())

def get_fy_details(fy_start_date, fy_end_date):
	start_year = getdate(fy_start_date).year
	if start_year == getdate(fy_end_date).year:
		fy = cstr(start_year)
	else:
		fy = cstr(start_year) + '-' + cstr(start_year + 1)
	return fy
