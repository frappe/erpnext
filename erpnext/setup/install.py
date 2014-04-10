# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def after_install():
	import_defaults()
	import_country_and_currency()
	from erpnext.accounts.doctype.chart_of_accounts.import_charts import import_charts
	import_charts()
	frappe.db.set_default('desktop:home_page', 'setup-wizard')
	feature_setup()
	from erpnext.setup.page.setup_wizard.setup_wizard import add_all_roles_to
	add_all_roles_to("Administrator")
	set_single_defaults()
	frappe.db.commit()

def import_country_and_currency():
	from frappe.country_info import get_all
	data = get_all()

	for name in data:
		country = frappe._dict(data[name])
		if not frappe.db.exists("Country", name):
			frappe.get_doc({
				"doctype": "Country",
				"country_name": name,
				"code": country.code,
				"date_format": country.date_format or "dd-mm-yyyy",
				"time_zones": "\n".join(country.timezones or [])
			}).insert()

		if country.currency and not frappe.db.exists("Currency", country.currency):
			frappe.get_doc({
				"doctype": "Currency",
				"currency_name": country.currency,
				"fraction": country.currency_fraction,
				"symbol": country.currency_symbol,
				"fraction_units": country.currency_fraction_units,
				"number_format": country.number_format
			}).insert()

def import_defaults():
	records = [
		# role
		{'doctype': "Role", "role_name": "Analytics"},

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

	from frappe.modules import scrub
	for r in records:
		doc = frappe.get_doc(r)

		# ignore mandatory for root
		parent_link_field = ("parent_" + scrub(doc.doctype))
		if doc.meta.get_field(parent_link_field) and not doc.get(parent_link_field):
			doc.ignore_mandatory = True

		doc.insert()

def feature_setup():
	"""save global defaults and features setup"""
	doc = frappe.get_doc("Features Setup", "Features Setup")
	doc.ignore_permissions = True

	# store value as 1 for all these fields
	flds = ['fs_item_serial_nos', 'fs_item_batch_nos', 'fs_brands', 'fs_item_barcode',
		'fs_item_advanced', 'fs_packing_details', 'fs_item_group_in_details',
		'fs_exports', 'fs_imports', 'fs_discounts', 'fs_purchase_discounts',
		'fs_after_sales_installations', 'fs_projects', 'fs_sales_extras',
		'fs_recurring_invoice', 'fs_pos', 'fs_manufacturing', 'fs_quality',
		'fs_page_break', 'fs_more_info', 'fs_pos_view'
	]
	doc.update(dict(zip(flds, [1]*len(flds))))
	doc.save()

def set_single_defaults():
	for dt in frappe.db.sql_list("""select name from `tabDocType` where issingle=1"""):
		default_values = frappe.db.sql("""select fieldname, `default` from `tabDocField`
			where parent=%s""", dt)
		if default_values:
			try:
				b = frappe.get_doc(dt, dt)
				for fieldname, value in default_values:
					b.set(fieldname, value)
				b.save()
			except frappe.MandatoryError:
				pass

	frappe.db.set_default("date_format", "dd-mm-yyyy")
