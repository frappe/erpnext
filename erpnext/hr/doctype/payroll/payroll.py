# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, flt, nowdate, add_days, getdate, fmt_money
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from frappe.model.document import Document

class Payroll(Document):
	def set_start_end_dates(self):
		self.update(get_start_end_dates(self.payroll_frequency, 
			self.start_date or self.posting_date, self.company))

	def validate(self):
		totals = get_total_salary_and_loan_amounts(self.name)
		if totals:
			self.total_payroll_amount = totals.rounded_total
		update_salary_slip_status(self.name, self.status)

def get_employee_list(payroll_frequency, company, salary_slip_based_on_timesheet, start_date, end_date, branch, department, designation):
	salary_structures = frappe.get_all("Salary Structure",filters = {"docstatus": ("!=",2), "is_active": 'Yes', "company": company, 
				"payroll_frequency": payroll_frequency, "salary_slip_based_on_timesheet": salary_slip_based_on_timesheet})	
	if salary_structures:
		employee_list = []
		for salary_structure in salary_structures:
			cond = get_joining_releiving_condition(start_date, end_date)
			cond += " and t2.parent = %(salary_structure)s"
			cond += " and t2.from_date <= %(start_date)s"
			cond += " and (t2.to_date is null or t2.to_date >= %(end_date)s)"
			if company:
				cond += "and t1.company = %(company)s"
			if branch:
				cond += "and t1.branch = %(branch)s"
			if department:
				cond += "and t1.department = %(department)s"
			if designation:
				cond += "and t1.designation = %(designation)s"

			employees = frappe.db.sql("""
				select
					t1.name
				from
					`tabEmployee` t1, `tabSalary Structure Employee` t2
				where
					t1.docstatus!=2
					and t1.name = t2.employee
			%s """% cond, {"salary_structure": salary_structure.name, "start_date": start_date, "end_date": end_date, 
							"company": company, "branch": branch, "department": department, "designation": designation})
			for employee in employees:
				if employee not in employee_list:
			    		employee_list.append(employee)
		return employee_list

def get_joining_releiving_condition(start_date, end_date):
	cond = """
		and ifnull(t1.date_of_joining, '0000-00-00') <= '%(end_date)s'
		and ifnull(t1.relieving_date, '2199-12-31') >= '%(start_date)s'
	""" % {"start_date": start_date, "end_date": end_date}
	return cond
	
def get_total_salary_and_loan_amounts(name):
	"""
		Get total loan principal, loan interest and salary amount from submitted salary slip based on selected criteria
	"""
	salary_slips = frappe.get_all("Payroll Salary Slip", filters = {"parent": name, "salary_slip_status":'Submitted'})		
	if salary_slips:
		totals = frappe.db.sql("""select sum(principal_amount) as total_principal_amount, sum(interest_amount) as total_interest_amount, 
			sum(total_loan_repayment) as total_loan_repayment, sum(rounded_total) as rounded_total from `tabSalary Slip` t1
			where t1.docstatus = 1 and name in (%s)""" %
					(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=True)
		return totals[0]

def get_loan_accounts(company):
	loan_accounts = frappe.get_all("Employee Loan", fields=["employee_loan_account", "interest_income_account"], 
		filters = {"company": company, "docstatus":1})
	if loan_accounts:
		return loan_accounts[0]	

def get_salary_component_account(company, salary_component):
	account = frappe.db.get_value("Salary Component Account",
		{"parent": salary_component, "company": company}, "default_account")

	if not account:
		frappe.throw(_("Please set default account in Salary Component {0}")
			.format(salary_component))
	return account

def get_salary_components(name, component_type):
	salary_slips = frappe.get_all("Payroll Salary Slip", filters = {"parent": name, "salary_slip_status":'Submitted'})
	if salary_slips:
		salary_components = frappe.db.sql("""select salary_component, amount, parentfield
			from `tabSalary Detail` where parentfield = '%s' and parent in (%s)""" %
			(component_type, ', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=True)
		return salary_components

def get_salary_component_total(name, company, component_type = None):
	salary_components = get_salary_components(name, component_type)
	if salary_components:
		component_dict = {}
		for item in salary_components:
			component_dict[item['salary_component']] = component_dict.get(item['salary_component'], 0) + item['amount']
		account_details = get_account(company, component_dict = component_dict)
		return account_details

def get_account(company, component_dict = None):
	account_dict = {}
	for s, a in component_dict.items():
		account = get_salary_component_account(company, s)
		account_dict[account] = account_dict.get(account, 0) + a
	return account_dict	
	
def get_default_payroll_payable_account(company):
	payroll_payable_account = frappe.db.get_value("Company",
		{"company_name": company}, "default_payroll_payable_account")

	if not payroll_payable_account:
		frappe.throw(_("Please set Default Payroll Payable Account in Company {0}")
			.format(company))
	return payroll_payable_account

@frappe.whitelist()
def create_salary_slips(start_date, end_date, company, payroll_frequency, posting_date,
	salary_slip_based_on_timesheet = 0, branch = None, department = None, designation = None):
	emp_list = get_employee_list(payroll_frequency, company, salary_slip_based_on_timesheet, start_date, end_date, branch, department, designation)
	salary_slips = []
	if not emp_list:
		frappe.msgprint(_("No Employees found in the selected criteria"))
	else:
		for emp in emp_list:
			if not frappe.db.sql("""select
					name from `tabSalary Slip`
				where
					docstatus!= 2 and
					employee = %s and
					start_date >= %s and
					end_date <= %s and
					company = %s
					""", (emp[0], start_date, end_date, company)):
				salary_slip = frappe.get_doc({
					"doctype": "Salary Slip",
					"salary_slip_based_on_timesheet": salary_slip_based_on_timesheet,
					"payroll_frequency": payroll_frequency,
					"start_date": start_date,
					"end_date": end_date,
					"employee": emp[0],
					"employee_name": frappe.get_value("Employee", {"name":emp[0]}, "employee_name"),
					"company": company,
					"posting_date": posting_date
				})
				salary_slip.insert()
				salary_slips.append(salary_slip)		
		return salary_slips

@frappe.whitelist()
def submit_salary_slips(name):
	salary_slips = frappe.get_all("Payroll Salary Slip", filters = {"parent": name, "salary_slip_status":'Draft'})
	submitted_salary_slips = []
	for salary_slip in salary_slips:
		ss_obj = frappe.get_doc("Salary Slip", salary_slip)
		if ss_obj.net_pay > 0 and ss_obj.status == "Draft":
			ss_obj.submit()
			submitted_salary_slips.append(ss_obj.name)
	return submitted_salary_slips

@frappe.whitelist()
def make_accural_jv_entry(name, company, start_date, end_date, cost_center = None, project = None):
	earnings = get_salary_component_total(name, company, component_type = "earnings") or {}
	deductions = get_salary_component_total(name, company, component_type = "deductions") or {}
	default_payroll_payable_account = get_default_payroll_payable_account(company)
	loan_amounts = get_total_salary_and_loan_amounts(name)
	loan_accounts = get_loan_accounts(company)

	if earnings or deductions:
		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = 'Journal Entry'
		journal_entry.user_remark = _('Accural Journal Entry for salaries from {0} to {1}').format(start_date, end_date)
		journal_entry.company = company
		journal_entry.posting_date = nowdate()
		journal_entry.reference_type = "Payroll"
		journal_entry.reference_name = name

		account_amt_list = []
		adjustment_amt = 0
		for acc, amt in earnings.items():
			adjustment_amt = adjustment_amt+amt
			account_amt_list.append({
					"account": acc,
					"debit_in_account_currency": amt,
					"cost_center": cost_center,
					"project": project,
					"reference_type": "Payroll",
					"reference_name": name
				})
		for acc, amt in deductions.items():
			adjustment_amt = adjustment_amt-amt
			account_amt_list.append({
					"account": acc,
					"credit_in_account_currency": amt,
					"cost_center": cost_center,
					"project": project,
					"reference_type": "Payroll",
					"reference_name": name
				})
		#employee loan
		if loan_amounts.total_loan_repayment:
			account_amt_list.append({
					"account": loan_accounts.employee_loan_account,
					"credit_in_account_currency": loan_amounts.total_principal_amount,
					"reference_type": "Payroll",
					"reference_name": name
				})
			account_amt_list.append({
					"account": loan_accounts.interest_income_account,
					"credit_in_account_currency": loan_amounts.total_interest_amount,
					"cost_center": cost_center,
					"project": project,
					"reference_type": "Payroll",
					"reference_name": name
				})
			adjustment_amt = adjustment_amt-(loan_amounts.total_loan_repayment)
		
		account_amt_list.append({
				"account": default_payroll_payable_account,
				"credit_in_account_currency": adjustment_amt,
				"reference_type": "Payroll",
				"reference_name": name
			})
		journal_entry.set("accounts", account_amt_list)
		return journal_entry.as_dict()

@frappe.whitelist()
def make_payment_entry(name, company, start_date, end_date, payment_account):
	total_salary_amount = get_total_salary_and_loan_amounts(name)
	default_payroll_payable_account = get_default_payroll_payable_account(company)

	if total_salary_amount.rounded_total:
		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = 'Bank Entry'
		journal_entry.user_remark = _('Payment of salary from {0} to {1}').format(start_date, end_date)
		journal_entry.company = company
		journal_entry.posting_date = nowdate()

		account_amt_list = []

		account_amt_list.append({
				"account": payment_account,
				"credit_in_account_currency": total_salary_amount.rounded_total,
				"reference_type": "Payroll",
				"reference_name": name
			})
		account_amt_list.append({
				"account": default_payroll_payable_account,
				"debit_in_account_currency": total_salary_amount.rounded_total,
				"reference_type": "Payroll",
				"reference_name": name
			})	
		journal_entry.set("accounts", account_amt_list)
	return journal_entry.as_dict()

@frappe.whitelist()
def get_start_end_dates(payroll_frequency, start_date = None, company = None):
	'''Returns dict of start and end dates for given payroll frequency based on start_date'''

	if payroll_frequency == "Monthly" or payroll_frequency == "Bimonthly" or payroll_frequency == "":
		fiscal_year = get_fiscal_year(start_date, company=company)[0]
		month = "%02d" % getdate(start_date).month
		m = get_month_details(fiscal_year, month)
		if payroll_frequency == "Bimonthly":
			if getdate(start_date).day <= 15:
				start_date = m['month_start_date']
				end_date = m['month_mid_end_date']
			else:
				start_date = m['month_mid_start_date']
				end_date = m['month_end_date']
		else:
			start_date = m['month_start_date']
			end_date = m['month_end_date']

	if payroll_frequency == "Weekly":
		end_date = add_days(start_date, 6)

	if payroll_frequency == "Fortnightly":
		end_date = add_days(start_date, 13)

	if payroll_frequency == "Daily":
		end_date = start_date

	return frappe._dict({
		'start_date': start_date, 'end_date': end_date
	})

def get_month_details(year, month):
	ysd = frappe.db.get_value("Fiscal Year", year, "year_start_date")
	if ysd:
		from dateutil.relativedelta import relativedelta
		import calendar, datetime
		diff_mnt = cint(month)-cint(ysd.month)
		if diff_mnt<0:
			diff_mnt = 12-int(ysd.month)+cint(month)
		msd = ysd + relativedelta(months=diff_mnt) # month start date
		month_days = cint(calendar.monthrange(cint(msd.year) ,cint(month))[1]) # days in month
		mid_start = datetime.date(msd.year, cint(month), 16) # month mid start date
		mid_end = datetime.date(msd.year, cint(month), 15) # month mid end date
		med = datetime.date(msd.year, cint(month), month_days) # month end date
		return frappe._dict({
			'year': msd.year,
			'month_start_date': msd,
			'month_end_date': med,
			'month_mid_start_date': mid_start,
			'month_mid_end_date': mid_end,
			'month_days': month_days
		})
	else:
		frappe.throw(_("Fiscal Year {0} not found").format(year))

def update_payment_status(doc):
	payroll_jv = frappe.db.sql("""select posting_date, ifnull(sum(debit_in_account_currency), 0) as payroll_amount 
		from `tabGL Entry` where against_voucher_type = 'Payroll' and against_voucher = %s""", 
		(doc.name), as_dict=1)[0]

	if payroll_jv.payroll_amount > 0:
		payroll_jv.payroll_amount = payroll_jv.payroll_amount + doc.total_amount_paid
		frappe.db.set_value("Payroll", doc.name , "total_amount_paid", payroll_jv.payroll_amount)
		if payroll_jv.payroll_amount == doc.total_payroll_amount:
			frappe.db.set_value("Payroll", doc.name , "status", "Paid")
		if payroll_jv.payroll_amount >doc.total_payroll_amount:
			frappe.throw(_("Paid Amount cannot be greater than Payroll Amount {0}").format(doc.total_payroll_amount))	

	if payroll_jv.payroll_amount == 0:
		frappe.db.set_value("Payroll", doc.name , "status", "Unpaid")
		frappe.db.set_value("Payroll", doc.name , "total_amount_paid", 0)

def update_salary_slip_status(name, status):
	salary_slips = frappe.get_all("Payroll Salary Slip", filters = {"parent": name, "salary_slip_status":'Submitted'})
	for salary_slip in salary_slips:
		if status == "Paid":
			frappe.db.set_value("Salary Slip", salary_slip.name, "status", "Paid")
		if status == "Unpaid":
			frappe.db.set_value("Salary Slip", salary_slip.name, "status", "Submitted")