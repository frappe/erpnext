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
	]

	for item in doctype_list:
		frappe.reload_doc(item['module'], 'doctype', item['doctype'])
	

	for item in doctype_list:
		all_doc = frappe.get_all(item['doctype'])
		if all_doc:
			for record in all_doc:
				doc = frappe.get_doc(item['doctype'], record)
				if doc.doctype == 'Employee Incentive':
					if not doc.company:
						doc.company = frappe.db.get_value('Employee', doc.get('employee'), 'company')
				if not doc.currency:
					doc.currency = frappe.db.get_value('Company', doc.get('company'), 'default_currency')
				if doc.doctype in ['Employee Advance', 'Payroll Entry', 'Salary Slip']:
					if not doc.exchange_rate:
						doc.exchange_rate = 1
				if doc.doctype in ['Payroll Entry', 'Salary Structure Assignment']:
					if not doc.payroll_payable_account:
						doc.payroll_payable_account = frappe.db.get_value('Company', doc.get('company'), 'default_payroll_payable_account')
					if doc.income_tax_slab:
						update_income_tax_slab(doc.income_tax_slab)
				if doc.doctype == 'Salary Slip':
					update_base(doc)
				doc.db_update()

def update_base(doc):
	if not doc.base_hour_rate:
		doc.base_hour_rate = doc.get('hour_rate')
	if not doc.base_gross_pay:
		doc.base_gross_pay = doc.get('gross_pay')
	if not doc.base_total_deduction:
		doc.base_total_deduction = doc.get('total_deduction')
	if not doc.base_net_pay:
		doc.base_net_pay = doc.get('net_pay')
	if not doc.base_rounded_total:
		doc.base_rounded_total = doc.get('rounded_total')
	if not doc.base_total_in_words:
		doc.base_total_in_words = doc.get('total_in_words')

def update_income_tax_slab(income_tax_slab):
	income_tax_slab_doc = frappe.get_doc('Income Tax Slab', income_tax_slab)
	if not income_tax_slab_doc.currency:
		income_tax_slab_doc.currency = doc.get('currency')
		income_tax_slab_doc.db_update()