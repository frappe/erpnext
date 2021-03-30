# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import formatdate
import itertools
from frappe import _, get_all

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
		}
	]

	if frappe.db.has_column('Employee', 'ifsc_code'):
		columns.append({
			"label": _("IFSC Code"),
			"fieldtype": "Data",
			"fieldname": "bank_code",
			"width": 100
		})

	columns += [{
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
	}]

	data = []

	accounts = get_bank_accounts()
	payroll_entries = get_payroll_entries(accounts, filters)
	salary_slips = get_salary_slips(payroll_entries)

	if frappe.db.has_column('Employee', 'ifsc_code'):
		get_emp_bank_ifsc_code(salary_slips)

	for salary in salary_slips:
		if salary.bank_name and salary.bank_account_no and salary.debit_acc_no and salary.status in ["Submitted", "Paid"]:
			row = {
				"payroll_no": salary.payroll_entry,
				"debit_account": salary.debit_acc_no,
				"payment_date": frappe.utils.formatdate(salary.modified.strftime('%Y-%m-%d')),
				"bank_name": salary.bank_name,
				"employee_account_no": salary.bank_account_no,
				"bank_code": salary.ifsc_code,
				"employee_name": salary.employee+": " + salary.employee_name,
				"currency": frappe.get_cached_value('Company', filters.company, 'default_currency'),
				"amount": salary.net_pay,
			}
			data.append(row)
	return columns, data

def get_bank_accounts():
	accounts = [d.name for d in get_all("Account", filters={"account_type": "Bank"})]
	return accounts

def get_payroll_entries(accounts, filters):
	payroll_filter = [
		('payment_account', 'IN', accounts),
		('number_of_employees', '>', 0),
		('Company', '=', filters.company)
	]
	if filters.to_date:
		payroll_filter.append(('posting_date', '<', filters.to_date))

	if filters.from_date:
		payroll_filter.append(('posting_date', '>', filters.from_date))

	entries = get_all("Payroll Entry", payroll_filter, ["name", "payment_account"])

	payment_accounts = [d.payment_account for d in entries]
	set_company_account(payment_accounts, entries)
	return entries

def get_salary_slips(payroll_entries):
	payroll  = [d.name for d in payroll_entries]
	salary_slips = get_all("Salary Slip", filters = [("payroll_entry", "IN", payroll)],
		fields = ["modified", "net_pay", "bank_name", "bank_account_no", "payroll_entry", "employee", "employee_name", "status"]
	)

	payroll_entry_map = {}
	for entry in payroll_entries:
		payroll_entry_map[entry.name] = entry

	# appending company debit accounts
	for slip in salary_slips:
		if slip.payroll_entry:
			slip["debit_acc_no"] = payroll_entry_map[slip.payroll_entry]['company_account']
		else:
			slip["debit_acc_no"] = None

	return salary_slips

def get_emp_bank_ifsc_code(salary_slips):
	emp_names = [d.employee for d in salary_slips]
	ifsc_codes = get_all("Employee", [("name", "IN", emp_names)], ["ifsc_code", "name"])

	ifsc_codes_map = {}
	for code in ifsc_codes:
		ifsc_codes_map[code.name] = code

	for slip in salary_slips:
		slip["ifsc_code"] = ifsc_codes_map[code.name]['ifsc_code']

	return salary_slips

def set_company_account(payment_accounts, payroll_entries):
	company_accounts = get_all("Bank Account", [("account", "in", payment_accounts)], ["account", "bank_account_no"])
	company_accounts_map = {}
	for acc in company_accounts:
		company_accounts_map[acc.account] = acc

	for entry in payroll_entries:
		company_account = ''
		if entry.payment_account in company_accounts_map:
			company_account = company_accounts_map[entry.payment_account]['bank_account_no']
		entry["company_account"] = company_account

	return payroll_entries
