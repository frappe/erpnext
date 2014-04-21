# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

from frappe import _

def install():
	records = [

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
		{'uom_name': _('Unit'), 'doctype': 'UOM', 'name': 'Unit', "must_be_whole_number": 1},
		{'uom_name': _('Box'), 'doctype': 'UOM', 'name': 'Box', "must_be_whole_number": 1},
		{'uom_name': _('Kg'), 'doctype': 'UOM', 'name': 'Kg'},
		{'uom_name': _('Nos'), 'doctype': 'UOM', 'name': 'Nos', "must_be_whole_number": 1},
		{'uom_name': _('Pair'), 'doctype': 'UOM', 'name': 'Pair', "must_be_whole_number": 1},
		{'uom_name': _('Set'), 'doctype': 'UOM', 'name': 'Set', "must_be_whole_number": 1},
		{'uom_name': _('Hour'), 'doctype': 'UOM', 'name': 'Hour'},
		{'uom_name': _('Minute'), 'doctype': 'UOM', 'name': 'Minute'},

	]

	from frappe.modules import scrub
	for r in records:
		doc = frappe.get_doc(r)

		# ignore mandatory for root
		parent_link_field = ("parent_" + scrub(doc.doctype))
		if doc.meta.get_field(parent_link_field) and not doc.get(parent_link_field):
			doc.ignore_mandatory = True

		doc.insert()
