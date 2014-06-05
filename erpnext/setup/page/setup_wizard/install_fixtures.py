# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

from frappe import _

def install(country=None):
	records = [

		# address template
		{'doctype':"Address Template", "country": country},

		# item group
		{'doctype': 'Item Group', 'item_group_name': _('All Item Groups'),
			'is_group': 'Yes', 'parent_item_group': ''},
		{'doctype': 'Item Group', 'item_group_name': _('Products'),
			'is_group': 'No', 'parent_item_group': _('All Item Groups'), "show_in_website": 1 },
		{'doctype': 'Item Group', 'item_group_name': _('Raw Material'),
			'is_group': 'No', 'parent_item_group': _('All Item Groups') },
		{'doctype': 'Item Group', 'item_group_name': _('Services'),
			'is_group': 'No', 'parent_item_group': _('All Item Groups') },
		{'doctype': 'Item Group', 'item_group_name': _('Sub Assemblies'),
			'is_group': 'No', 'parent_item_group': _('All Item Groups') },
		{'doctype': 'Item Group', 'item_group_name': _('Consumable'),
			'is_group': 'No', 'parent_item_group': _('All Item Groups') },

		# deduction type
		{'doctype': 'Deduction Type', 'name': _('Income Tax'), 'description': _('Income Tax'), 'deduction_name': _('Income Tax')},

		# earning type
		{'doctype': 'Earning Type', 'name': _('Basic'), 'description': _('Basic'), 'earning_name': _('Basic'), 'taxable': 'Yes'},

		# expense claim type
		{'doctype': 'Expense Claim Type', 'name': _('Calls'), 'expense_type': _('Calls')},
		{'doctype': 'Expense Claim Type', 'name': _('Food'), 'expense_type': _('Food')},
		{'doctype': 'Expense Claim Type', 'name': _('Medical'), 'expense_type': _('Medical')},
		{'doctype': 'Expense Claim Type', 'name': _('Others'), 'expense_type': _('Others')},
		{'doctype': 'Expense Claim Type', 'name': _('Travel'), 'expense_type': _('Travel')},

		# leave type
		{'doctype': 'Leave Type', 'leave_type_name': _('Casual Leave'), 'name': _('Casual Leave'), 'is_encash': 1, 'is_carry_forward': 1, 'max_days_allowed': '3', },
		{'doctype': 'Leave Type', 'leave_type_name': _('Compensatory Off'), 'name': _('Compensatory Off'), 'is_encash': 0, 'is_carry_forward': 0, },
		{'doctype': 'Leave Type', 'leave_type_name': _('Sick Leave'), 'name': _('Sick Leave'), 'is_encash': 0, 'is_carry_forward': 0, },
		{'doctype': 'Leave Type', 'leave_type_name': _('Privilege Leave'), 'name': _('Privilege Leave'), 'is_encash': 0, 'is_carry_forward': 0, },
		{'doctype': 'Leave Type', 'leave_type_name': _('Leave Without Pay'), 'name': _('Leave Without Pay'), 'is_encash': 0, 'is_carry_forward': 0, 'is_lwp':1},

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
		{'doctype': 'Designation', 'designation_name': _('Assistant')},
		{'doctype': 'Designation', 'designation_name': _('Researcher')},

		# territory
		{'doctype': 'Territory', 'territory_name': _('All Territories'), 'is_group': 'Yes', 'name': _('All Territories'), 'parent_territory': ''},

		# customer group
		{'doctype': 'Customer Group', 'customer_group_name': _('All Customer Groups'), 'is_group': 'Yes', 	'name': _('All Customer Groups'), 'parent_customer_group': ''},
		{'doctype': 'Customer Group', 'customer_group_name': _('Individual'), 'is_group': 'No', 'parent_customer_group': _('All Customer Groups')},
		{'doctype': 'Customer Group', 'customer_group_name': _('Commercial'), 'is_group': 'No', 'parent_customer_group': _('All Customer Groups')},
		{'doctype': 'Customer Group', 'customer_group_name': _('Non Profit'), 'is_group': 'No', 'parent_customer_group': _('All Customer Groups')},
		{'doctype': 'Customer Group', 'customer_group_name': _('Government'), 'is_group': 'No', 'parent_customer_group': _('All Customer Groups')},

		# supplier type
		{'doctype': 'Supplier Type', 'supplier_type': _('Services')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Local')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Raw Material')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Electrical')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Hardware')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Pharmaceutical')},
		{'doctype': 'Supplier Type', 'supplier_type': _('Distributor')},

		# Sales Person
		{'doctype': 'Sales Person', 'sales_person_name': _('Sales Team'), 'is_group': "Yes", "parent_sales_person": ""},

		# UOM
		{'uom_name': _('Unit'), 'doctype': 'UOM', 'name': _('Unit'), "must_be_whole_number": 1},
		{'uom_name': _('Box'), 'doctype': 'UOM', 'name': _('Box'), "must_be_whole_number": 1},
		{'uom_name': _('Kg'), 'doctype': 'UOM', 'name': _('Kg')},
		{'uom_name': _('Nos'), 'doctype': 'UOM', 'name': _('Nos'), "must_be_whole_number": 1},
		{'uom_name': _('Pair'), 'doctype': 'UOM', 'name': _('Pair'), "must_be_whole_number": 1},
		{'uom_name': _('Set'), 'doctype': 'UOM', 'name': _('Set'), "must_be_whole_number": 1},
		{'uom_name': _('Hour'), 'doctype': 'UOM', 'name': _('Hour')},
		{'uom_name': _('Minute'), 'doctype': 'UOM', 'name': _('Minute')},

		# Mode of Payment
		{'doctype': 'Mode of Payment', 'mode_of_payment': 'Check' if country=="United States" else _('Cheque')},
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Cash')},
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Credit Card')},
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Wire Transfer')},
		{'doctype': 'Mode of Payment', 'mode_of_payment': _('Bank Draft')},

		# Activity Type
		{'doctype': 'Activity Type', 'activity_type': _('Planning')},
		{'doctype': 'Activity Type', 'activity_type': _('Research')},
		{'doctype': 'Activity Type', 'activity_type': _('Proposal Writing')},
		{'doctype': 'Activity Type', 'activity_type': _('Execution')},
		{'doctype': 'Activity Type', 'activity_type': _('Communication')},

		# Industry Type
		{'doctype': 'Industry Type', 'industry': _('Accounting')},
		{'doctype': 'Industry Type', 'industry': _('Advertising')},
		{'doctype': 'Industry Type', 'industry': _('Aerospace')},
		{'doctype': 'Industry Type', 'industry': _('Agriculture')},
		{'doctype': 'Industry Type', 'industry': _('Airline')},
		{'doctype': 'Industry Type', 'industry': _('Apparel & Accessories')},
		{'doctype': 'Industry Type', 'industry': _('Automotive')},
		{'doctype': 'Industry Type', 'industry': _('Banking')},
		{'doctype': 'Industry Type', 'industry': _('Biotechnology')},
		{'doctype': 'Industry Type', 'industry': _('Broadcasting')},
		{'doctype': 'Industry Type', 'industry': _('Brokerage')},
		{'doctype': 'Industry Type', 'industry': _('Chemical')},
		{'doctype': 'Industry Type', 'industry': _('Computer')},
		{'doctype': 'Industry Type', 'industry': _('Consulting')},
		{'doctype': 'Industry Type', 'industry': _('Consumer Products')},
		{'doctype': 'Industry Type', 'industry': _('Cosmetics')},
		{'doctype': 'Industry Type', 'industry': _('Defense')},
		{'doctype': 'Industry Type', 'industry': _('Department Stores')},
		{'doctype': 'Industry Type', 'industry': _('Education')},
		{'doctype': 'Industry Type', 'industry': _('Electronics')},
		{'doctype': 'Industry Type', 'industry': _('Energy')},
		{'doctype': 'Industry Type', 'industry': _('Entertainment & Leisure')},
		{'doctype': 'Industry Type', 'industry': _('Executive Search')},
		{'doctype': 'Industry Type', 'industry': _('Financial Services')},
		{'doctype': 'Industry Type', 'industry': _('Food, Beverage & Tobacco')},
		{'doctype': 'Industry Type', 'industry': _('Grocery')},
		{'doctype': 'Industry Type', 'industry': _('Health Care')},
		{'doctype': 'Industry Type', 'industry': _('Internet Publishing')},
		{'doctype': 'Industry Type', 'industry': _('Investment Banking')},
		{'doctype': 'Industry Type', 'industry': _('Legal')},
		{'doctype': 'Industry Type', 'industry': _('Manufacturing')},
		{'doctype': 'Industry Type', 'industry': _('Motion Picture & Video')},
		{'doctype': 'Industry Type', 'industry': _('Music')},
		{'doctype': 'Industry Type', 'industry': _('Newspaper Publishers')},
		{'doctype': 'Industry Type', 'industry': _('Online Auctions')},
		{'doctype': 'Industry Type', 'industry': _('Pension Funds')},
		{'doctype': 'Industry Type', 'industry': _('Pharmaceuticals')},
		{'doctype': 'Industry Type', 'industry': _('Private Equity')},
		{'doctype': 'Industry Type', 'industry': _('Publishing')},
		{'doctype': 'Industry Type', 'industry': _('Real Estate')},
		{'doctype': 'Industry Type', 'industry': _('Retail & Wholesale')},
		{'doctype': 'Industry Type', 'industry': _('Securities & Commodity Exchanges')},
		{'doctype': 'Industry Type', 'industry': _('Service')},
		{'doctype': 'Industry Type', 'industry': _('Soap & Detergent')},
		{'doctype': 'Industry Type', 'industry': _('Software')},
		{'doctype': 'Industry Type', 'industry': _('Sports')},
		{'doctype': 'Industry Type', 'industry': _('Technology')},
		{'doctype': 'Industry Type', 'industry': _('Telecommunications')},
		{'doctype': 'Industry Type', 'industry': _('Television')},
		{'doctype': 'Industry Type', 'industry': _('Transportation')},
		{'doctype': 'Industry Type', 'industry': _('Venture Capital')}
	]

	from frappe.modules import scrub
	for r in records:
		doc = frappe.new_doc(r.get("doctype"))
		doc.update(r)

		# ignore mandatory for root
		parent_link_field = ("parent_" + scrub(doc.doctype))
		if doc.meta.get_field(parent_link_field) and not doc.get(parent_link_field):
			doc.ignore_mandatory = True

		doc.insert()
