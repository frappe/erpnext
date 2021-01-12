# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.utils import get_currency_precision
from erpnext.payroll.doctype.salary_structure_assignment.salary_structure_assignment import get_employee_currency

def execute(filters=None):
	if not filters: filters = {}

	expense_claims = get_expense_claims(filters)
	columns = get_columns()

	if not expense_claims:
		return columns, expense_claims

	data = get_data(expense_claims, filters)
	return columns, data

def get_columns():
	return [
		{
			'label': _('Posting Date'),
			'fieldname': 'posting_date',
			'fieldtype': 'Date',
			'width': 120
		},
		{
			'label': _('Expense Claim'),
			'fieldname': 'name',
			'fieldtype': 'Link',
			'options': 'Expense Claim',
			'width': 120
		},
		{
			'label': _('Employee'),
			'fieldname': 'employee',
			'fieldtype': 'Link',
			'options': 'Employee',
			'width': 120
		},
		{
			'label': _('Employee Name'),
			'fieldname': 'employee_name',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'label': _('Expense Approver'),
			'fieldname': 'expense_approver',
			'fieldtype': 'Link',
			'options': 'User',
			'width': 120
		},
		{
			'label': _('Grand Total'),
			'fieldname': 'grand_total',
			'fieldtype': 'Currency',
			'options': 'currency',
			'width': 150
		},
		{
			'label': _('Advance Amount'),
			'fieldname': 'total_advance_amount',
			'fieldtype': 'Currency',
			'options': 'currency',
			'width': 150
		},
		{
			'label': _('Outstanding Amount'),
			'fieldname': 'outstanding_amount',
			'fieldtype': 'Currency',
			'options': 'currency',
			'width': 150
		},
		{
			'label': _('Company'),
			'fieldname': 'company',
			'fieldtype': 'Link',
			'options': 'Company',
			'width': 120
		},
		{
			'label': _('Status'),
			'fieldname': 'status',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'label': _('Approval Status'),
			'fieldname': 'approval_status',
			'fieldtype': 'Data',
			'width': 120
		}
	]

def get_conditions(filters):
	conditions = {}

	if filters.get('employee'):
		conditions['employee'] = filters.employee

	if filters.get('company'):
		conditions['company'] = filters.company

	if filters.get('status'):
		conditions['status'] = filters.status

	if filters.get('approval_status'):
		conditions['approval_status'] = filters.approval_status

	if filters.get('from_date'):
		conditions['posting_date'] = ('>=', filters.from_date)

	if filters.get('to_date'):
		conditions['posting_date'] = ('<=', filters.to_date)

	return conditions

def get_expense_claims(filters):
	conditions = get_conditions(filters)
	conditions['docstatus'] = ('<', 2)

	return frappe.db.get_list('Expense Claim',
		fields = ['posting_date', 'name', 'employee', 'employee_name', 'expense_approver', 'status',
			'approval_status', 'grand_total', 'base_grand_total', 'total_advance_amount', 'outstanding_amount',
			'currency', 'conversion_rate', 'company'],
		filters = conditions,
		order_by = 'posting_date, name desc'
	)

def get_data(expense_claims, filters):
	currency_precision = get_currency_precision() or 2
	company_currency = frappe.get_cached_value('Company', filters.get('company'), 'default_currency')

	for claim in expense_claims:
		employee_currency = get_employee_currency(claim.employee)

		if filters.get('employee'):
			claim.currency = employee_currency
		else:
			claim.currency = company_currency

		if filters.get('employee') and claim.currency == employee_currency:
			claim['grand_total'] = claim.grand_total
		else:
			claim['grand_total'] = claim.base_grand_total

			claim['total_advance_amount'] = flt(flt(claim.total_advance_amount) *
				flt(claim.conversion_rate), currency_precision)

			claim['outstanding_amount'] = flt(flt(claim.outstanding_amount) *
				flt(claim.conversion_rate), currency_precision)

	return expense_claims