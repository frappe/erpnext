# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes

def post_import():
	webnotes.conn.begin()

	# feature setup
	import_defaults()
	import_country_and_currency()
	
	# home page
	webnotes.conn.set_value('Control Panel', None, 'home_page', 'setup-wizard')

	# features
	feature_setup()
	
	# all roles to Administrator
	from setup.page.setup_wizard.setup_wizard import add_all_roles_to
	add_all_roles_to("Administrator")
	
	webnotes.conn.commit()

def feature_setup():
	"""save global defaults and features setup"""
	bean = webnotes.bean("Features Setup", "Features Setup")
	bean.ignore_permissions = True

	# store value as 1 for all these fields
	flds = ['fs_item_serial_nos', 'fs_item_batch_nos', 'fs_brands', 'fs_item_barcode',
		'fs_item_advanced', 'fs_packing_details', 'fs_item_group_in_details',
		'fs_exports', 'fs_imports', 'fs_discounts', 'fs_purchase_discounts',
		'fs_after_sales_installations', 'fs_projects', 'fs_sales_extras',
		'fs_recurring_invoice', 'fs_pos', 'fs_manufacturing', 'fs_quality',
		'fs_page_break', 'fs_more_info', 'fs_pos_view'
	]
	bean.doc.fields.update(dict(zip(flds, [1]*len(flds))))
	bean.save()

def import_country_and_currency():
	from webnotes.country_info import get_all
	data = get_all()
	
	for name in data:
		country = webnotes._dict(data[name])
		webnotes.doc({
			"doctype": "Country",
			"country_name": name,
			"date_format": country.date_format or "dd-mm-yyyy",
			"time_zones": "\n".join(country.timezones or [])
		}).insert()
		
		if country.currency and not webnotes.conn.exists("Currency", country.currency):
			webnotes.doc({
				"doctype": "Currency",
				"currency_name": country.currency,
				"fraction": country.currency_fraction,
				"symbol": country.currency_symbol,
				"fraction_units": country.currency_fraction_units,
				"number_format": country.number_format
			}).insert()

def import_defaults():
	records = [
		# item group
		{'doctype': 'Item Group', 'item_group_name': 'All Item Groups', 'is_group': 'Yes', 'parent_item_group': ''},
		{'doctype': 'Item Group', 'item_group_name': 'Products', 'is_group': 'No', 'parent_item_group': 'All Item Groups'},
		{'doctype': 'Item Group', 'item_group_name': 'Raw Material', 'is_group': 'No', 'parent_item_group': 'All Item Groups'},
		{'doctype': 'Item Group', 'item_group_name': 'Services', 'is_group': 'No', 'parent_item_group': 'All Item Groups'},
		{'doctype': 'Item Group', 'item_group_name': 'Sub Assemblies', 'is_group': 'No', 'parent_item_group': 'All Item Groups'},
		{'doctype': 'Item Group', 'item_group_name': 'Consumable', 'is_group': 'No', 'parent_item_group': 'All Item Groups'},
		
		# deduction type
		{'doctype': 'Deduction Type', 'name': 'Income Tax', 'description': 'Income Tax', 'deduction_name': 'Income Tax'},
		{'doctype': 'Deduction Type', 'name': 'Professional Tax', 'description': 'Professional Tax', 'deduction_name': 'Professional Tax'},
		{'doctype': 'Deduction Type', 'name': 'Provident Fund', 'description': 'Provident fund', 'deduction_name': 'Provident Fund'},
		
		# earning type
		{'doctype': 'Earning Type', 'name': 'Basic', 'description': 'Basic', 'earning_name': 'Basic', 'taxable': 'Yes'},
		{'doctype': 'Earning Type', 'name': 'House Rent Allowance', 'description': 'House Rent Allowance', 'earning_name': 'House Rent Allowance', 'taxable': 'No'},
		
		# expense claim type
		{'doctype': 'Expense Claim Type', 'name': 'Calls', 'expense_type': 'Calls'},
		{'doctype': 'Expense Claim Type', 'name': 'Food', 'expense_type': 'Food'},
		{'doctype': 'Expense Claim Type', 'name': 'Medical', 'expense_type': 'Medical'},
		{'doctype': 'Expense Claim Type', 'name': 'Others', 'expense_type': 'Others'},
		{'doctype': 'Expense Claim Type', 'name': 'Travel', 'expense_type': 'Travel'},
		
		# leave type
		{'doctype': 'Leave Type', 'leave_type_name': 'Casual Leave', 'name': 'Casual Leave', 'is_encash': 1, 'is_carry_forward': 1, 'max_days_allowed': '3', },
		{'doctype': 'Leave Type', 'leave_type_name': 'Compensatory Off', 'name': 'Compensatory Off', 'is_encash': 0, 'is_carry_forward': 0, },
		{'doctype': 'Leave Type', 'leave_type_name': 'Sick Leave', 'name': 'Sick Leave', 'is_encash': 0, 'is_carry_forward': 0, },
		{'doctype': 'Leave Type', 'leave_type_name': 'Privilege Leave', 'name': 'Privilege Leave', 'is_encash': 0, 'is_carry_forward': 0, },
		{'doctype': 'Leave Type', 'leave_type_name': 'Leave Without Pay', 'name': 'Leave Without Pay', 'is_encash': 0, 'is_carry_forward': 0, 'is_lwp':1},
		
		# territory
		{'doctype': 'Territory', 'territory_name': 'All Territories', 'is_group': 'Yes', 'name': 'All Territories', 'parent_territory': ''},
			
		# customer group
		{'doctype': 'Customer Group', 'customer_group_name': 'All Customer Groups', 'is_group': 'Yes', 	'name': 'All Customer Groups', 'parent_customer_group': ''},
		{'doctype': 'Customer Group', 'customer_group_name': 'Individual', 'is_group': 'No', 'parent_customer_group': 'All Customer Groups'},
		{'doctype': 'Customer Group', 'customer_group_name': 'Commercial', 'is_group': 'No', 'parent_customer_group': 'All Customer Groups'},
		{'doctype': 'Customer Group', 'customer_group_name': 'Non Profit', 'is_group': 'No', 'parent_customer_group': 'All Customer Groups'},
		{'doctype': 'Customer Group', 'customer_group_name': 'Government', 'is_group': 'No', 'parent_customer_group': 'All Customer Groups'},
			
		# supplier type
		{'doctype': 'Supplier Type', 'supplier_type': 'Services'},
		{'doctype': 'Supplier Type', 'supplier_type': 'Local'},
		{'doctype': 'Supplier Type', 'supplier_type': 'Raw Material'},
		{'doctype': 'Supplier Type', 'supplier_type': 'Electrical'},
		{'doctype': 'Supplier Type', 'supplier_type': 'Hardware'},
		{'doctype': 'Supplier Type', 'supplier_type': 'Pharmaceutical'},
		{'doctype': 'Supplier Type', 'supplier_type': 'Distributor'},
		
		# Sales Person
		{'doctype': 'Sales Person', 'sales_person_name': 'Sales Team', 'is_group': "Yes", "parent_sales_person": ""},
		
		# UOM
		{'uom_name': 'Unit', 'doctype': 'UOM', 'name': 'Unit', "must_be_whole_number": 1}, 
		{'uom_name': 'Box', 'doctype': 'UOM', 'name': 'Box', "must_be_whole_number": 1}, 
		{'uom_name': 'Kg', 'doctype': 'UOM', 'name': 'Kg'}, 
		{'uom_name': 'Nos', 'doctype': 'UOM', 'name': 'Nos', "must_be_whole_number": 1}, 
		{'uom_name': 'Pair', 'doctype': 'UOM', 'name': 'Pair', "must_be_whole_number": 1}, 
		{'uom_name': 'Set', 'doctype': 'UOM', 'name': 'Set', "must_be_whole_number": 1}, 
		{'uom_name': 'Hour', 'doctype': 'UOM', 'name': 'Hour'},
		{'uom_name': 'Minute', 'doctype': 'UOM', 'name': 'Minute'}, 
	]
	
	from webnotes.modules import scrub
	for r in records:
		bean = webnotes.bean(r)
		
		# ignore mandatory for root
		parent_link_field = ("parent_" + scrub(bean.doc.doctype))
		if parent_link_field in bean.doc.fields and not bean.doc.fields.get(parent_link_field):
			bean.ignore_mandatory = True
		
		bean.insert()