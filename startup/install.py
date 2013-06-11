from __future__ import unicode_literals

import webnotes

def pre_import():
	webnotes.conn.begin()
	make_modules()
	make_roles()
	webnotes.conn.commit()
	
def make_modules():
	modules = [
		" Home", " System", " Utilities", " Website", " Setup",
		" Selling", " Buying", " Projects", " Accounts", " Stock",
		" Support", " HR", " Manufacturing"]
	
	for m in modules:
		doc = webnotes.doc(fielddata = {
			"doctype": "Module Def",
			"module_name": m,
		})
		doc.insert()
	
def make_roles():
	roles = [
		"Accounts Manager", "Accounts User", "Analytics", "Auditor",
		"Blogger", "Customer", "Employee", "Expense Approver",
		"HR Manager", "HR User", "Leave Approver", "Maintenance Manager",
		"Maintenance User", "Manufacturing Manager", "Manufacturing User",
		"Material Manager", "Material Master Manager", "Material User",
		"Partner", "Projects User", "Projects Manager", "Purchase Manager", "Purchase Master Manager",
		"Purchase User", "Quality Manager", "Sales Manager",
		"Sales Master Manager", "Sales User", "Supplier", "Support Manager",
		"Support Team", "Website Manager"]
		
	for r in roles:
		doc = webnotes.doc(fielddata = {
			"doctype":"Role",
			"role_name": r
		})
		doc.insert()

def post_import():
	webnotes.conn.begin()
	# feature setup
	import_defaults()
	import_country_and_currency()
	
	# home page
	webnotes.conn.set_value('Control Panel', None, 'home_page', 'desktop')

	# features
	feature_setup()
	
	# all roles to Administrator
	from setup.doctype.setup_control.setup_control import add_all_roles_to
	add_all_roles_to("Administrator")
	
	webnotes.conn.commit()

def feature_setup():
	"""save global defaults and features setup"""
	doc = webnotes.doc("Features Setup", "Features Setup")

	# store value as 1 for all these fields
	flds = ['fs_item_serial_nos', 'fs_item_batch_nos', 'fs_brands', 'fs_item_barcode',
		'fs_item_advanced', 'fs_packing_details', 'fs_item_group_in_details',
		'fs_exports', 'fs_imports', 'fs_discounts', 'fs_purchase_discounts',
		'fs_after_sales_installations', 'fs_projects', 'fs_sales_extras',
		'fs_recurring_invoice', 'fs_pos', 'fs_manufacturing', 'fs_quality',
		'fs_page_break', 'fs_more_info'
	]
	doc.fields.update(dict(zip(flds, [1]*len(flds))))
	doc.save()

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
		{'doctype': 'Item Group', 'item_group_name': 'All Item Groups', 'is_group': 'Yes', 'name': 'All Item Groups', 'parent_item_group': ''},
		{'doctype': 'Item Group', 'item_group_name': 'Default', 'is_group': 'No', 'name': 'Default', 'parent_item_group': 'All Item Groups'},
		
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
		{'doctype': 'Territory', 'territory_name': 'Default', 'is_group': 'No', 'name': 'Default', 'parent_territory': 'All Territories'},
			
		# customer group
		{'doctype': 'Customer Group', 'customer_group_name': 'All Customer Groups', 'is_group': 'Yes', 	'name': 'All Customer Groups', 'parent_customer_group': ''},
		{'doctype': 'Customer Group', 'customer_group_name': 'Default Customer Group', 'is_group': 'No', 'name': 'Default Customer Group', 'parent_customer_group': 'All Customer Groups'},
			
		# supplier type
		{'doctype': 'Supplier Type', 'name': 'Default Supplier Type', 'supplier_type': 'Default Supplier Type'},
		
		# Price List
		{'doctype': 'Price List', 'name': 'Default Price List', 'price_list_name': 'Default Price List'},
		{'doctype': 'Price List', 'name': 'Standard', 'price_list_name': 'Standard'},
				
		# warehouse type
		{'doctype': 'Warehouse Type', 'name': 'Default Warehouse Type', 'warehouse_type': 'Default Warehouse Type'},
		{'doctype': 'Warehouse Type', 'name': 'Fixed Asset', 'warehouse_type': 'Fixed Asset'},
		{'doctype': 'Warehouse Type', 'name': 'Reserved', 'warehouse_type': 'Reserved'},
		{'doctype': 'Warehouse Type', 'name': 'Rejected', 'warehouse_type': 'Rejected'},
		{'doctype': 'Warehouse Type', 'name': 'Sample', 'warehouse_type': 'Sample'},
		{'doctype': 'Warehouse Type', 'name': 'Stores', 'warehouse_type': 'Stores'},
		{'doctype': 'Warehouse Type', 'name': 'WIP Warehouse', 'warehouse_type': 'WIP Warehouse'},
		
		# warehouse 
		{'doctype': 'Warehouse', 'warehouse_name': 'Default Warehouse', 'name': 'Default Warehouse', 'warehouse_type': 'Default Warehouse Type'},
			
		# Workstation
		{'doctype': 'Workstation', 'name': 'Default Workstation', 'workstation_name': 'Default Workstation', 'warehouse': 'Default Warehouse'},
		
		# Sales Person
		{'doctype': 'Sales Person', 'name': 'All Sales Persons', 'sales_person_name': 'All Sales Persons', 'is_group': "Yes", "parent_sales_person": ""},
		
		# UOM
		{'uom_name': 'Unit', 'doctype': 'UOM', 'name': 'Unit'}, 
		{'uom_name': 'Box', 'doctype': 'UOM', 'name': 'Box'}, 
		{'uom_name': 'Ft', 'doctype': 'UOM', 'name': 'Ft'}, 
		{'uom_name': 'Kg', 'doctype': 'UOM', 'name': 'Kg'}, 
		{'uom_name': 'Ltr', 'doctype': 'UOM', 'name': 'Ltr'}, 
		{'uom_name': 'Meter', 'doctype': 'UOM', 'name': 'Meter'}, 
		{'uom_name': 'Mtr', 'doctype': 'UOM', 'name': 'Mtr'}, 
		{'uom_name': 'Nos', 'doctype': 'UOM', 'name': 'Nos'}, 
		{'uom_name': 'Pair', 'doctype': 'UOM', 'name': 'Pair'}, 
		{'uom_name': 'Set', 'doctype': 'UOM', 'name': 'Set'}, 
		{'uom_name': 'Hour', 'doctype': 'UOM', 'name': 'Hour'}, 
		{'uom_name': 'Minute', 'doctype': 'UOM', 'name': 'Minute'}, 
	]
	
	for r in records:
		doc = webnotes.doc(r)
		doc.insert()
	