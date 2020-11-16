# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, erpnext
from frappe.model.utils.rename_field import rename_field

def execute():

	frappe.reload_doc('Accounts', 'doctype', 'Salary Component Account')
	if frappe.db.has_column('Salary Component Account', 'default_account'):
		rename_field("Salary Component Account", "default_account", "account")

	doctype_list = [
		{
		'module':'HR',
		'doctype':'Employee Advance'
		},
		{
		'module':'HR',
		'doctype':'Leave Encashment'
		},
		{
		'module':'Payroll',
		'doctype':'Additional Salary'
		},
		{
		'module':'Payroll',
		'doctype':'Employee Benefit Application'
		},
		{
		'module':'Payroll',
		'doctype':'Employee Benefit Claim'
		},
		{
		'module':'Payroll',
		'doctype':'Employee Incentive'
		},
		{
		'module':'Payroll',
		'doctype':'Payroll Entry'
		},
		{
		'module':'Payroll',
		'doctype':'Retention Bonus'
		},
		{
		'module':'Payroll',
		'doctype':'Salary Structure'
		},
		{
		'module':'Payroll',
		'doctype':'Salary Structure Assignment'
		},
		{
		'module':'Payroll',
		'doctype':'Salary Slip'
		},
		{
		'module':'Payroll',
		'doctype':'Income Tax Slab'
		},
	]

	for item in doctype_list:
		frappe.reload_doc(item['module'], 'doctype', item['doctype'])
	
	for item in doctype_list:
		if item['doctype'] != 'Income Tax Slab':
			all_doc = frappe.get_all(item['doctype'])
			if all_doc:
				for record in all_doc:
					if item['doctype'] in ['Payroll Entry', 'Salary Structure']:
						company = frappe.db.get_value(item['doctype'], record, 'company')
					else:
						employee = frappe.db.get_value(item['doctype'], record, 'employee')
						company = frappe.db.get_value('Employee', employee, 'company')
					currency = frappe.db.get_value('Company', company, 'default_currency')
					if item['doctype'] == 'Employee Incentive':
						if not frappe.db.get_value(item['doctype'], record, 'company'):
							frappe.db.set_value(item['doctype'], record, 'company', company)
					if not frappe.db.get_value(item['doctype'], record, 'currency'):
						frappe.db.set_value(item['doctype'], record, 'currency', currency)
					if item['doctype'] in ['Employee Advance', 'Payroll Entry', 'Salary Slip']:
						if not frappe.db.get_value(item['doctype'], record, 'exchange_rate'):
							frappe.db.set_value(item['doctype'], record, 'exchange_rate', '1'))
					if item['doctype'] in ['Payroll Entry', 'Salary Structure Assignment']:
						if not frappe.db.get_value(item['doctype'], record, 'payroll_payable_account'):
							frappe.db.set_value(item['doctype'], record, 'payroll_payable_account', frappe.db.get_value('Company', company, 'default_payroll_payable_account')))
					if item['doctype'] in ['Salary Structure', 'Salary Structure Assignment']:
						if frappe.db.get_value(item['doctype'], record, 'income_tax_slab'):
							if not frappe.db.get_value('Income Tax Slab', frappe.db.get_value(item['doctype'], record, 'income_tax_slab'), 'currency'):
								frappe.db.set_value('Income Tax Slab', frappe.db.get_value(item['doctype'], record, 'income_tax_slab'), 'currency', currency)
					if item['doctype'] == 'Salary Slip':
						update_base('Salary Slip', record)

def update_base(doctype, record):
	if not frappe.db.get_value(doctype, record, 'base_hour_rate'):
		frappe.db.set_value(doctype, record, 'base_hour_rate', frappe.db.get_value(doctype, record, 'hour_rate'))
	if not frappe.db.get_value(doctype, record, 'base_gross_pay'):
		frappe.db.set_value(doctype, record, 'base_gross_pay', frappe.db.get_value(doctype, record, 'gross_pay'))
	if not frappe.db.get_value(doctype, record, 'base_total_deduction'):
		frappe.db.set_value(doctype, record, 'base_total_deduction', frappe.db.get_value(doctype, record, 'total_deduction'))
	if not frappe.db.get_value(doctype, record, 'base_net_pay'):
		frappe.db.set_value(doctype, record, 'base_net_pay', frappe.db.get_value(doctype, record, 'net_pay'))
	if not frappe.db.get_value(doctype, record, 'base_rounded_total'):
		frappe.db.set_value(doctype, record, 'base_rounded_total', frappe.db.get_value(doctype, record, 'rounded_total'))
	if not frappe.db.get_value(doctype, record, 'base_total_in_words'):
		frappe.db.set_value(doctype, record, 'base_total_in_words', frappe.db.get_value(doctype, record, 'total_in_words'))
