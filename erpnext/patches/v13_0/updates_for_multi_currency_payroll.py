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
		'doctype':'Employee Tax Exemption Declaration'
		},
		{
		'module':'Payroll',
		'doctype':'Employee Tax Exemption Proof Submission'
		},
		{
		'module':'Payroll',
		'doctype':'Income Tax Slab'
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

	base_keys = [
		{
			"base_key": "base_hour_rate",
			"key": "hour_rate"
		},
		{
			"base_key": "base_gross_pay",
			"key": "gross_pay"
		},
		{
			"base_key": "base_total_deduction",
			"key": "total_deduction"
		},
		{
			"base_key": "base_net_pay",
			"key": "net_pay"
		},
		{
			"base_key": "base_rounded_total",
			"key": "rounded_total"
		},
		{
			"base_key": "base_total_in_words",
			"key": "total_in_words"
		},
	]

	for item in doctype_list:
		frappe.reload_doc(item['module'], 'doctype', item['doctype'])
		all_doc = frappe.get_all(item['doctype'])
		if all_doc:
			for record in all_doc:
				if item['doctype'] in [
					'Employee Advance', 
					'Leave Encashment', 
					'Employee Benefit Application',
					'Employee Benefit Claim', 
					'Employee Incentive'
					]:

					if not frappe.db.get_value(item['doctype'], record, 'currency'):
						frappe.db.set_value(
							item['doctype'], record, 'currency', frappe.db.get_value(
								'Company', frappe.db.get_value(
									'Employee', frappe.db.get_value(
										item['doctype'], record, 'employee'
									), 'company'
								), 'default_currency'
							)
						)

				if item['doctype'] == 'Employee Advance':

					if not frappe.db.get_value('Employee Advance', record, 'exchange_rate'):
						frappe.db.set_value('Employee Advance', record, 'exchange_rate', 1)

				if item['doctype'] in [
					'Additional Salary', 
					'Employee Tax Exemption Declaration', 
					'Employee Tax Exemption Proof Submission', 
					'Income Tax Slab', 
					'Payroll Entry', 
					'Retention Bonus', 
					'Salary Structure', 
					'Salary Structure Assignment', 
					'Salary Slip'
					]:

					if not frappe.db.get_value(item['doctype'], record, 'currency'):
						frappe.db.set_value(
							item['doctype'], record, 'currency', frappe.db.get_value(
								'Company', frappe.db.get_value(
									item['doctype'], record, 'company'
								), 'default_currency'
							)
						)

				if item['doctype'] == 'Employee Incentive':
					if not frappe.db.get_value('Employee Incentive', record, 'company'):
						frappe.db.set_value(
							'Employee Incentive', record, 'company', frappe.db.get_value(
								'Employee', frappe.db.get_value(
									'Employee Incentive', record, 'employee'
								), 'company'
							)
						)

				if item['doctype'] in ['Payroll Entry', 'Salary Slip']:
					if not frappe.db.get_value(item['doctype'], record, 'exchange_rate'):
						frappe.db.set_value(item['doctype'], record, 'exchange_rate', 1)

					if item['doctype'] == 'Salary Slip':
						update_base('Salary Slip', record)

				if item['doctype'] in ['Salary Structure Assignment', 'Payroll Entry']:

					if not frappe.db.get_value(item['doctype'], record, 'payroll_payable_account'):
						payroll_payable_account = frappe.db.get_value(
								'Company', frappe.db.get_value(
									item['doctype'], record, 'company'
								), 'default_payable_account'
							)

						if not payroll_payable_account:
							payroll_payable_account = frappe.db.get_value("Account",
							{"account_name": _("Payroll Payable"), "company": frappe.db.get_value(
									item['doctype'], record, 'company'
								), "is_group": 0})

						frappe.db.set_value(item['doctype'], record, 'payroll_payable_account', payroll_payable_account)

def update_base(doctype, record):
	for item in base_keys:
		if not frappe.db.get_value(doctype, record, item['base_key']):
			frappe.db.set_value(doctype, record, item['base_key'], frappe.db.get_value(doctype, record, item['key']))