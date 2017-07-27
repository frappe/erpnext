# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

from frappe import _

default_lead_sources = ["Existing Customer", "Reference", "Advertisement",
	"Cold Calling", "Exhibition", "Supplier Reference", "Mass Mailing",
	"Customer's Vendor", "Campaign", "Walk In"]

def install(country=None):
	records = [
		# domains
		{ 'doctype': 'Domain', 'domain': _('Distribution')},
		{ 'doctype': 'Domain', 'domain': _('Manufacturing')},
		{ 'doctype': 'Domain', 'domain': _('Retail')},
		{ 'doctype': 'Domain', 'domain': _('Services')},
		{ 'doctype': 'Domain', 'domain': _('Education')},

		# address template
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
		{'doctype': 'Salary Component', 'salary_component': _('Income Tax'), 'description': _('Income Tax'), 'type': 'Deduction'},
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
			'is_encash': 1, 'is_carry_forward': 1, 'max_days_allowed': '3', 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Compensatory Off'), 'name': _('Compensatory Off'),
			'is_encash': 0, 'is_carry_forward': 0, 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Sick Leave'), 'name': _('Sick Leave'),
			'is_encash': 0, 'is_carry_forward': 0, 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Privilege Leave'), 'name': _('Privilege Leave'),
			'is_encash': 0, 'is_carry_forward': 0, 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Leave Without Pay'), 'name': _('Leave Without Pay'),
			'is_encash': 0, 'is_carry_forward': 0, 'is_lwp':1, 'include_holiday': 1},

		# Employment Type
		{'doctype': 'Employment Type', 'employee_type_name': _('Full-time')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Part-time')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Probation')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Contract')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Commission')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Piecework')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Intern')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Apprentice')},

		# Department
		{'doctype': 'Department', 'department_name': _('Accounts')},
		{'doctype': 'Department', 'department_name': _('Marketing')},
		{'doctype': 'Department', 'department_name': _('Sales')},
		{'doctype': 'Department', 'department_name': _('Purchase')},
		{'doctype': 'Department', 'department_name': _('Operations')},
		{'doctype': 'Department', 'department_name': _('Production')},
		{'doctype': 'Department', 'department_name': _('Dispatch')},
		{'doctype': 'Department', 'department_name': _('Customer Service')},
		{'doctype': 'Department', 'department_name': _('Human Resources')},
		{'doctype': 'Department', 'department_name': _('Management')},
		{'doctype': 'Department', 'department_name': _('Quality Management')},
		{'doctype': 'Department', 'department_name': _('Research & Development')},
		{'doctype': 'Department', 'department_name': _('Legal')},

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

		# territory
		{'doctype': 'Territory', 'territory_name': _('All Territories'), 'is_group': 1, 'name': _('All Territories'), 'parent_territory': ''},

		# customer group
		{'doctype': 'Customer Group', 'customer_group_name': _('All Customer Groups'), 'is_group': 1, 	'name': _('All Customer Groups'), 'parent_customer_group': ''},
		{'doctype': 'Customer Group', 'customer_group_name': _('Individual'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
		{'doctype': 'Customer Group', 'customer_group_name': _('Commercial'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
		{'doctype': 'Customer Group', 'customer_group_name': _('Non Profit'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
		{'doctype': 'Customer Group', 'customer_group_name': _('Government'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},

		# supplier type
		{'doctype': 'Supplier Type', 'supplier_type': _('Services')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Local')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Raw Material')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Electrical')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Hardware')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Pharmaceutical')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Distributor')},

		# Sales Person
		{'doctype': 'Sales Person', 'sales_person_name': _('Sales Team'), 'is_group': 1, "parent_sales_person": ""},

		# UOM
		{'uom_name': _('Unit'), 'doctype': 'UOM', 'name': _('Unit'), "must_be_whole_number": 1},
		{'uom_name': _('Box'), 'doctype': 'UOM', 'name': _('Box'), "must_be_whole_number": 1},
		{'uom_name': _('Kg'), 'doctype': 'UOM', 'name': _('Kg')},
		{'uom_name': _('Meter'), 'doctype': 'UOM', 'name': _('Meter')},
		{'uom_name': _('Litre'), 'doctype': 'UOM', 'name': _('Litre')},
		{'uom_name': _('Gram'), 'doctype': 'UOM', 'name': _('Gram')},
		{'uom_name': _('Nos'), 'doctype': 'UOM', 'name': _('Nos'), "must_be_whole_number": 1},
		{'uom_name': _('Pair'), 'doctype': 'UOM', 'name': _('Pair'), "must_be_whole_number": 1},
		{'uom_name': _('Set'), 'doctype': 'UOM', 'name': _('Set'), "must_be_whole_number": 1},
		{'uom_name': _('Hour'), 'doctype': 'UOM', 'name': _('Hour')},
		{'uom_name': _('Minute'), 'doctype': 'UOM', 'name': _('Minute')},

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

		# Lead Source
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

		{'doctype': "Email Account", "email_id": "sales@example.com", "append_to": "Opportunity"},
		{'doctype': "Email Account", "email_id": "support@example.com", "append_to": "Issue"},
		{'doctype': "Email Account", "email_id": "jobs@example.com", "append_to": "Job Applicant"},

		{'doctype': "Party Type", "party_type": "Customer"},
		{'doctype': "Party Type", "party_type": "Supplier"},
		{'doctype': "Party Type", "party_type": "Employee"},

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

	]

	from erpnext.setup.setup_wizard.industry_type import get_industry_types
	records += [{"doctype":"Industry Type", "industry": d} for d in get_industry_types()]
	# records += [{"doctype":"Operation", "operation": d} for d in get_operations()]

	records += [{'doctype': 'Lead Source', 'source_name': _(d)} for d in default_lead_sources]

	# Records for the Supplier Scorecard
	from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import make_default_records
	make_default_records()

	from frappe.modules import scrub
	for r in records:
		doc = frappe.new_doc(r.get("doctype"))
		doc.update(r)

		# ignore mandatory for root
		parent_link_field = ("parent_" + scrub(doc.doctype))
		if doc.meta.get_field(parent_link_field) and not doc.get(parent_link_field):
			doc.flags.ignore_mandatory = True

		try:
			doc.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError as e:
			# pass DuplicateEntryError and continue
			if e.args and e.args[0]==doc.doctype and e.args[1]==doc.name:
				# make sure DuplicateEntryError is for the exact same doc and not a related doc
				pass
			else:
				raise
