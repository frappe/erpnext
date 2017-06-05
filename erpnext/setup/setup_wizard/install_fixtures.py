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
		{'doctype': 'Salary Component', 'salary_component': _('Pension'), 'description': _('Pension'), 'type': 'Deduction'},
		{'doctype': 'Salary Component', 'salary_component': _('Social Security'), 'description': _('Social Security'), 'type': 'Deduction'},
		{'doctype': 'Salary Component', 'salary_component': _('Income Tax'), 'description': _('Income Tax'), 'type': 'Deduction'},
		{'doctype': 'Salary Component', 'salary_component': _('Student Loan'), 'description': _('Student Loan'), 'type': 'Deduction'},
		{'doctype': 'Salary Component', 'salary_component': _('Salary'), 'description': _('Salary'), 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': _('Wages'), 'description': _('Wages'), 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': _('Commission'), 'description': _('Commission'), 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': _('Leave Encashment'), 'description': _('Leave Encashment'), 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': _('Arrear'), 'description': _('Arrear'), 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': _('Bonus'), 'description': _('Bonus'), 'type': 'Earning'},
		

		# expense claim type
		{'doctype': 'Expense Claim Type', 'name': _('Telephone'), 'expense_type': _('Telephone')},
		{'doctype': 'Expense Claim Type', 'name': _('Food'), 'expense_type': _('Food')},
		{'doctype': 'Expense Claim Type', 'name': _('Accommodation'), 'expense_type': _('Accommodation')},
		{'doctype': 'Expense Claim Type', 'name': _('Travel'), 'expense_type': _('Travel')},
		{'doctype': 'Expense Claim Type', 'name': _('Medical'), 'expense_type': _('Medical')},
		{'doctype': 'Expense Claim Type', 'name': _('Entertainment'), 'expense_type': _('Entertainment')},
		{'doctype': 'Expense Claim Type', 'name': _('Gift'), 'expense_type': _('Gift')},
		{'doctype': 'Expense Claim Type', 'name': _('Other'), 'expense_type': _('Other')},

		# leave type
		{'doctype': 'Leave Type', 'leave_type_name': _('Casual Leave'), 'name': _('Casual Leave'),
			'is_encash': 1, 'is_carry_forward': 1, 'max_days_allowed': '3', 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Privilege Leave'), 'name': _('Privilege Leave'),
			'is_encash': 0, 'is_carry_forward': 0, 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Annual Leave'), 'name': _('Annual Leave'),
			'is_encash': 1, 'is_carry_forward': 1, 'max_days_allowed': '39', 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Compensatory Time-off'), 'name': _('Compensatory Time-off'),
			'is_encash': 0, 'is_carry_forward': 0, 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Sick Leave'), 'name': _('Sick Leave'),
			'is_encash': 0, 'is_carry_forward': 0, 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Maternity Leave'), 'name': _('Maternity Leave'),
			'is_encash': 0, 'is_carry_forward': 0, 'max_days_allowed': '364', 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Paternity Leave'), 'name': _('Paternity Leave'),
			'is_encash': 0, 'is_carry_forward': 0, 'max_days_allowed': '14', 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Adoption Leave'), 'name': _('Paternity Leave'),
			'is_encash': 0, 'is_carry_forward': 0, 'max_days_allowed': '182', 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Sick Leave'), 'name': _('Sick Leave'),
			'is_encash': 0, 'is_carry_forward': 0, 'include_holiday': 1},
		{'doctype': 'Leave Type', 'leave_type_name': _('Unpaid Leave'), 'name': _('Unpaid Leave'),
			'is_encash': 0, 'is_carry_forward': 0, 'is_lwp':1, 'include_holiday': 1},

		# Employment Type
		{'doctype': 'Employment Type', 'employee_type_name': _('Full-time')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Full-time, Under Probation')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Part-time')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Part-time, Under Probation')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Fixed-term')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Temporary')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Internship')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Apprenticeship')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Agency')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Freelance')},
		{'doctype': 'Employment Type', 'employee_type_name': _('Zero-hour')},

		# Department
		{'doctype': 'Department', 'department_name': _('Management')},
		{'doctype': 'Department', 'department_name': _('Finance')},
		{'doctype': 'Department', 'department_name': _('Operations')},
		{'doctype': 'Department', 'department_name': _('Production')},
		{'doctype': 'Department', 'department_name': _('Marketing')},
		{'doctype': 'Department', 'department_name': _('IT')},
		{'doctype': 'Department', 'department_name': _('Legal')},

		# Designation
		{'doctype': 'Designation', 'designation_name': _('Intern')},
		{'doctype': 'Designation', 'designation_name': _('Apprentice')},
		{'doctype': 'Designation', 'designation_name': _('Associate')},
		{'doctype': 'Designation', 'designation_name': _('Senior Associate')},
		{'doctype': 'Designation', 'designation_name': _('Executive')},
		{'doctype': 'Designation', 'designation_name': _('Senior Executive')},
		{'doctype': 'Designation', 'designation_name': _('Assistant Manager')},
		{'doctype': 'Designation', 'designation_name': _('Manager')},
		{'doctype': 'Designation', 'designation_name': _('Senior Manager')},
		{'doctype': 'Designation', 'designation_name': _('Chief Executive Officer')},
		{'doctype': 'Designation', 'designation_name': _('Chief Financial Officer')},
		{'doctype': 'Designation', 'designation_name': _('Chief Operating Officer')},
		{'doctype': 'Designation', 'designation_name': _('Chief Production Officer')},
		{'doctype': 'Designation', 'designation_name': _('Chief Marketing Officer')},
		{'doctype': 'Designation', 'designation_name': _('Chief Technology Officer')},
		{'doctype': 'Designation', 'designation_name': _('Chief Legal Officer')},
		{'doctype': 'Designation', 'designation_name': _('Deputy Director')},
		{'doctype': 'Designation', 'designation_name': _('Director')},
		{'doctype': 'Designation', 'designation_name': _('Managing Director')},
		{'doctype': 'Designation', 'designation_name': _('Partner')},
		{'doctype': 'Designation', 'designation_name': _('Senior Partner')},
		{'doctype': 'Designation', 'designation_name': _('Managing Partner')},
		{'doctype': 'Designation', 'designation_name': _('Vice President')},
		{'doctype': 'Designation', 'designation_name': _('President')},

		# territory
		{'doctype': 'Territory', 'territory_name': _('All Territories'), 'is_group': 1, 'name': _('All Territories'), 'parent_territory': ''},

		# customer group
		{'doctype': 'Customer Group', 'customer_group_name': _('All Customer Groups'), 'is_group': 1, 	'name': _('All Customer Groups'), 'parent_customer_group': ''},
		{'doctype': 'Customer Group', 'customer_group_name': _('Individual'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
		{'doctype': 'Customer Group', 'customer_group_name': _('Commercial'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
		{'doctype': 'Customer Group', 'customer_group_name': _('Non-profit'), 'is_group': 0, 'parent_customer_group': _('All Customer Groups')},
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
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Debit/Credit Card'),
			'type': 'Bank'},
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Charge Card'),
			'type': 'Bank'},
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Wire transfer'),
			'type': 'Bank'},
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Banker\'s draft'),
			'type': 'Bank'},

		# Activity Type
		{'doctype': 'Activity Type', 'activity_type': _('Initiating')},
		{'doctype': 'Activity Type', 'activity_type': _('Planning')},
		{'doctype': 'Activity Type', 'activity_type': _('Executing')},
		{'doctype': 'Activity Type', 'activity_type': _('Monitoring and Controlling')},
		{'doctype': 'Activity Type', 'activity_type': _('Closing')},

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
		except frappe.DuplicateEntryError, e:
			# pass DuplicateEntryError and continue
			if e.args and e.args[0]==doc.doctype and e.args[1]==doc.name:
				# make sure DuplicateEntryError is for the exact same doc and not a related doc
				pass
			else:
				raise
