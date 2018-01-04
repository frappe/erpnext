# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

from frappe import _
from frappe.desk.page.setup_wizard.setup_wizard import insert_records

default_lead_sources = ["Existing Customer", "Reference", "Advertisement",
	"Cold Calling", "Exhibition", "Supplier Reference", "Mass Mailing",
	"Customer's Vendor", "Campaign", "Walk In"]

def install(country=None):
	records = []
	for key, value in get_fixtures(country).iteritems():
		for record in value:
			record['doctype'] = key
			records.append(record)

	from erpnext.setup.setup_wizard.data.industry_type import get_industry_types
	records += [{"doctype":"Industry Type", "industry": d} for d in get_industry_types()]
	records += [{'doctype': 'Lead Source', 'source_name': _(d)} for d in default_lead_sources]

	# Records for the Supplier Scorecard
	from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import make_default_records
	make_default_records()

	return records

def get_fixtures(country=None):
	return {
		'Domain': [
			{'domain': 'Distribution'},
			{'domain': 'Manufacturing'},
			{'domain': 'Retail'},
			{'domain': 'Services'},
			{'domain': 'Education'},
			{'domain': 'Healthcare'},
			{'domain': 'Agriculture'},
			{'domain': 'Non Profit'}
		],

		'Item Group': [
			{'item_group_name': _('All Item Groups'), 	'is_group': 1, 'parent_item_group': ''},
			{'item_group_name': _('Products'), 			'is_group': 0, 'parent_item_group': _('All Item Groups'), "show_in_website": 1 },
			{'item_group_name': _('Raw Material'),		'is_group': 0, 'parent_item_group': _('All Item Groups') },
			{'item_group_name': _('Services'), 			'is_group': 0, 'parent_item_group': _('All Item Groups') },
			{'item_group_name': _('Sub Assemblies'), 	'is_group': 0, 'parent_item_group': _('All Item Groups') },
			{'item_group_name': _('Consumable'), 		'is_group': 0, 'parent_item_group': _('All Item Groups') }
		],

		'Territory': [
			{'territory_name': _('All Territories'), 'is_group': 1, 'name': _('All Territories'), 'parent_territory': ''}
		],

		'Address Template': [
			{"country": country}
		],

		'Salary Component': [
			{'salary_component': _('Income Tax'), 		'description': _('Income Tax'), 'type': 'Deduction'},
			{'salary_component': _('Basic'), 			'description': _('Basic'), 'type': 'Earning'},
			{'salary_component': _('Arrear'), 			'description': _('Arrear'), 'type': 'Earning'},
			{'salary_component': _('Leave Encashment'), 'description': _('Leave Encashment'), 'type': 'Earning'}
		],

		'Expense Claim Type': [
			{'name': _('Calls'), 	'expense_type': _('Calls')},
			{'name': _('Food'), 	'expense_type': _('Food')},
			{'name': _('Medical'), 	'expense_type': _('Medical')},
			{'name': _('Others'), 	'expense_type': _('Others')},
			{'name': _('Travel'), 	'expense_type': _('Travel')},
		],

		'Leave Type': [
			{'leave_type_name': _('Casual Leave'), 'name': _('Casual Leave'),
				'is_encash': 1, 'is_carry_forward': 1, 'max_days_allowed': '3', 'include_holiday': 1},
			{'leave_type_name': _('Compensatory Off'), 'name': _('Compensatory Off'),
				'is_encash': 0, 'is_carry_forward': 0, 'include_holiday': 1},
			{'leave_type_name': _('Sick Leave'), 'name': _('Sick Leave'),
				'is_encash': 0, 'is_carry_forward': 0, 'include_holiday': 1},
			{'leave_type_name': _('Privilege Leave'), 'name': _('Privilege Leave'),
				'is_encash': 0, 'is_carry_forward': 0, 'include_holiday': 1},
			{'leave_type_name': _('Leave Without Pay'), 'name': _('Leave Without Pay'),
				'is_encash': 0, 'is_carry_forward': 0, 'is_lwp':1, 'include_holiday': 1},
		],

		'Employment Type': [
			{'employee_type_name': _('Full-time')},
			{'employee_type_name': _('Part-time')},
			{'employee_type_name': _('Probation')},
			{'employee_type_name': _('Contract')},
			{'employee_type_name': _('Commission')},
			{'employee_type_name': _('Piecework')},
			{'employee_type_name': _('Intern')},
			{'employee_type_name': _('Apprentice')},
		],

		'Department': [
			{'department_name': _('Accounts')},
			{'department_name': _('Marketing')},
			{'department_name': _('Sales')},
			{'department_name': _('Purchase')},
			{'department_name': _('Operations')},
			{'department_name': _('Production')},
			{'department_name': _('Dispatch')},
			{'department_name': _('Customer Service')},
			{'department_name': _('Human Resources')},
			{'department_name': _('Management')},
			{'department_name': _('Quality Management')},
			{'department_name': _('Research & Development')},
			{'department_name': _('Legal')},
		],

		'Designation': [
			{'designation_name': _('CEO')},
			{'designation_name': _('Manager')},
			{'designation_name': _('Analyst')},
			{'designation_name': _('Engineer')},
			{'designation_name': _('Accountant')},
			{'designation_name': _('Secretary')},
			{'designation_name': _('Associate')},
			{'designation_name': _('Administrative Officer')},
			{'designation_name': _('Business Development Manager')},
			{'designation_name': _('HR Manager')},
			{'designation_name': _('Project Manager')},
			{'designation_name': _('Head of Marketing and Sales')},
			{'designation_name': _('Software Developer')},
			{'designation_name': _('Designer')},
			{'designation_name': _('Researcher')},
		],

		'Customer Group': [
			{'customer_group_name': _('All Customer Groups'), 'is_group': 1, 	'name': _('All Customer Groups'), 'parent_customer_group': ''},
			{'customer_group_name': _('Individual'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
			{'customer_group_name': _('Commercial'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
			{'customer_group_name': _('Non Profit'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
			{'customer_group_name': _('Government'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
		],

		'Sales Person': [
			{'sales_person_name': _('Sales Team'), 'is_group': 1, "parent_sales_person": ""}
		],

		'Supplier Type': [
			{'supplier_type': _('Services')},
			{'supplier_type': _('Local')},
			{'supplier_type': _('Raw Material')},
			{'supplier_type': _('Electrical')},
			{'supplier_type': _('Hardware')},
			{'supplier_type': _('Pharmaceutical')},
			{'supplier_type': _('Distributor')},
		],

		'UOM': [
			{'uom_name': _('Unit'), 	'name': _('Unit'), "must_be_whole_number": 1},
			{'uom_name': _('Box'), 		'name': _('Box'), "must_be_whole_number": 1},
			{'uom_name': _('Kg'), 		'name': _('Kg')},
			{'uom_name': _('Meter'), 	'name': _('Meter')},
			{'uom_name': _('Litre'),	'name': _('Litre')},
			{'uom_name': _('Gram'), 	'name': _('Gram')},
			{'uom_name': _('Nos'), 		'name': _('Nos'), "must_be_whole_number": 1},
			{'uom_name': _('Pair'), 	'name': _('Pair'), "must_be_whole_number": 1},
			{'uom_name': _('Set'), 		'name': _('Set'), "must_be_whole_number": 1},
			{'uom_name': _('Hour'), 	'name': _('Hour')},
			{'uom_name': _('Minute'), 	'name': _('Minute')},
		],

		'Mode of Payment': [
			{'mode_of_payment': _('Check') if country=="United States" else _('Cheque'), 'type': 'Bank'},
			{'mode_of_payment': _('Cash'), 			'type': 'Cash'},
			{'mode_of_payment': _('Credit Card'), 	'type': 'Bank'},
			{'mode_of_payment': _('Wire Transfer'), 'type': 'Bank'},
			{'mode_of_payment': _('Bank Draft'),	'type': 'Bank'},
		],

		'Activity Type': [
			{'activity_type': _('Planning')},
			{'activity_type': _('Research')},
			{'activity_type': _('Proposal Writing')},
			{'activity_type': _('Execution')},
			{'activity_type': _('Communication')},
		],

		'Assessment Group': [
			{'assessment_group_name': _('All Assessment Groups'), 'is_group': 1, 'parent_assessment_group': ''}
		],

		'Item Attribute': [
			{"attribute_name": _("Size"), "item_attribute_values": [
				{"attribute_value": _("Extra Small"), "abbr": "XS"},
				{"attribute_value": _("Small"), "abbr": "S"},
				{"attribute_value": _("Medium"), "abbr": "M"},
				{"attribute_value": _("Large"), "abbr": "L"},
				{"attribute_value": _("Extra Large"), "abbr": "XL"}
			]},

			{"attribute_name": _("Colour"), "item_attribute_values": [
				{"attribute_value": _("Red"), "abbr": "RED"},
				{"attribute_value": _("Green"), "abbr": "GRE"},
				{"attribute_value": _("Blue"), "abbr": "BLU"},
				{"attribute_value": _("Black"), "abbr": "BLA"},
				{"attribute_value": _("White"), "abbr": "WHI"}
			]},
		],

		'Email Account': [
			{"email_id": "sales@example.com", "append_to": "Opportunity"},
			{"email_id": "support@example.com", "append_to": "Issue"},
			{"email_id": "jobs@example.com", "append_to": "Job Applicant"},
		],

		'Party Type': [
			{"party_type": "Customer"},
			{"party_type": "Supplier"},
			{"party_type": "Employee"},
			{"party_type": "Member"},
		],

		'Opportunity Type': [
			{"name": _("Hub")},
			{"name": _("Sales")},
			{"name": _("Support")},
			{"name": _("Maintenance")},
		],

		'Project Type': [
			{"project_type": "Internal"},
			{"project_type": "External"},
			{"project_type": "Other"},
		],

		'Offer Term': [
			{"offer_term": _("Date of Joining")},
			{"offer_term": _("Annual Salary")},
			{"offer_term": _("Probationary Period")},
			{"offer_term": _("Employee Benefits")},
			{"offer_term": _("Working Hours")},
			{"offer_term": _("Stock Options")},
			{"offer_term": _("Department")},
			{"offer_term": _("Job Description")},
			{"offer_term": _("Responsibilities")},
			{"offer_term": _("Leaves per Year")},
			{"offer_term": _("Notice Period")},
			{"offer_term": _("Incentives")},
		],

		'Print Heading': [
			{'print_heading': _("Credit Note")},
			{'print_heading': _("Debit Note")},
		]
	}
