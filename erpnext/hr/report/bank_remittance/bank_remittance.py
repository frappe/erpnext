# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import formatdate
import itertools
from frappe import _

def execute(filters=None):
	columns = [
		{
			"label": _("Payroll Number"),
			"fieldtype": "Link",
			"fieldname": "payroll_no",
			"options": "Payroll Entry",
			"width": 150
		},
		{
			"label": _("Debit A/C Number"),
			"fieldtype": "Int",
			"fieldname": "debit_account",
			"hidden": 1,
			"width": 200
		},
		{
			"label": _("Payment Date"),
			"fieldtype": "Data",
			"fieldname": "payment_date",
			"width": 100
		},
		{
			"label": _("Employee Name"),
			"fieldtype": "Link",
			"fieldname": "employee_name",
			"options": "Employee",
			"width": 200
		},
		{
			"label": _("Bank Name"),
			"fieldtype": "Data",
			"fieldname": "bank_name",
			"width": 50
		},
		{
			"label": _("Employee A/C Number"),
			"fieldtype": "Int",
			"fieldname": "employee_account_no",
			"width": 50
		},
		{
			"label": _("IFSC Code"),
			"fieldtype": "Data",
			"fieldname": "bank_code",
			"width": 100
		},
		{
			"label": _("Currency"),
			"fieldtype": "Data",
			"fieldname": "currency",
			"width": 50
		},
		{
			"label": _("Net Salary Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"fieldname": "amount",
			"width": 100
		}
	]
	data = []

	accounts = get_account()
	payroll_entries = get_payroll_entry(accounts, filters)
	salary_slips = get_salary_slips(payroll_entries)
	get_emp_bank_ifsc_code(salary_slips)

	for salary in salary_slips:
		if salary.bank_name and salary.bank_account_no and salary.debit_acc_no and salary.status in ["Submitted", "Paid"]:
			row = {
					"payroll_no": salary.payroll_entry,
					"debit_account": salary.debit_acc_no,
					"payment_date": frappe.utils.formatdate(salary.modified.strftime('%Y-%m-%d')),
					"bank_name":salary.bank_name,
					"employee_account_no":salary.bank_account_no,
					"bank_code": salary.ifsc_code,
					"employee_name": salary.employee+": " + salary.employee_name,
					"currency": frappe.get_cached_value('Company', filters.company, 'default_currency'),
					"amount": salary.net_pay,
				}

			data.append(row)
	return columns, data

def get_account():
	accounts = frappe.get_all("Account",
	filters={
		"account_type": "Bank"
	}, as_list =1)

	return accounts

def get_payroll_entry(accounts, filters):
	accounts = list(itertools.chain(*accounts))
	accounts = ', '.join(map(str, accounts))
	payroll_filter = [
			('payment_account', 'IN', accounts),
			('number_of_employees', '>', 0),
			('Company', '=', filters.company)
		]
	if filters.to_date:
		payroll_filter.append(('posting_date', '<', filters.to_date))

	if filters.from_date:
		payroll_filter.append(('posting_date', '>', filters.from_date))

	entries = get_record("Payroll Entry", payroll_filter, ["name", "payment_account"])

	p = list(map(lambda x: {k:v for k, v in x.items() if k == 'payment_account'}, entries))
	payment_accounts = ', '.join(map(str, [l['payment_account'] for l in p if 'payment_account' in l]))
	get_company_account(payment_accounts, entries)
	return entries

def get_salary_slips(payroll_entries):
	d = list(map(lambda x: {k:v for k, v in x.items() if k == 'name'}, payroll_entries))
	payroll = ', '.join(map(str, [l['name'] for l in d if 'name' in l]))
	salary_slips = get_record("Salary Slip", [("payroll_entry", "IN", payroll)],
		fields = ["modified", "net_pay", "bank_name", "bank_account_no", "payroll_entry", "employee", "employee_name", "status"]
	)

	# appending company debit accounts
	for slip in salary_slips:
		for entry in payroll_entries:
			if slip.payroll_entry == entry.name:
				slip["debit_acc_no"] = entry.company_account

	return salary_slips

def get_emp_bank_ifsc_code(salary_slips):
	d = list(map(lambda x: {k:v for k, v in x.items() if k == 'employee'}, salary_slips))
	emp_names = ', '.join(map(str, [l['employee'] for l in d if 'employee' in l]))
	ifsc_codes = get_record("Employee", [("name", "IN", emp_names)], ["ifsc_code", "name"])
	for slip in salary_slips:
		for code in ifsc_codes:
			if code.name == slip.employee:
				slip["ifsc_code"] = code.ifsc_code

	return salary_slips

def get_company_account(payment_accounts ,payroll_entries):
	company_accounts = get_record("Bank Account", [("account", "IN", payment_accounts)], ["account", "bank_account_no"])
	for acc in company_accounts:
		for entry in payroll_entries:
			if acc.account == entry.payment_account:
				entry["company_account"] = acc.bank_account_no

	return payroll_entries

def get_record(doctype, filter, fields):
	return frappe.get_all(doctype, filters=filter, fields=fields)





