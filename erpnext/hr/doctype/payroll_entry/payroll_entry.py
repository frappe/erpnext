# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT
from frappe import _
from erpnext.accounts.utils import get_fiscal_year


class PayrollEntry(Document):

	def on_submit(self):
		self.create_salary_slips()

	def get_emp_list(self):
		"""
			Returns list of active employees based on selected criteria
			and for which salary structure exists
		"""
		cond = self.get_filter_condition()
		cond += self.get_joining_releiving_condition()

		condition = ''
		if self.payroll_frequency:
			condition = """and payroll_frequency = '%(payroll_frequency)s'"""% {"payroll_frequency": self.payroll_frequency}

		sal_struct = frappe.db.sql("""
				select
					name from `tabSalary Structure`
				where
					docstatus != 2 and
					is_active = 'Yes'
					and company = %(company)s and
					ifnull(salary_slip_based_on_timesheet,0) = %(salary_slip_based_on_timesheet)s
					{condition}""".format(condition=condition),
				{"company": self.company, "salary_slip_based_on_timesheet":self.salary_slip_based_on_timesheet})

		if sal_struct:
			cond += "and t2.parent IN %(sal_struct)s "
			emp_list = frappe.db.sql("""
				select
					t1.name as employee, t1.employee_name, t1.department, t1.designation
				from
					`tabEmployee` t1, `tabSalary Structure Employee` t2
				where
					t1.docstatus!=2
					and t1.name = t2.employee
			%s """% cond, {"sal_struct": sal_struct}, as_dict=True)
			return emp_list

	def fill_employee_details(self):
		self.set('employees', [])
		employees = self.get_emp_list()
		if not employees:
			frappe.throw(_("No employees for the mentioned criteria"))

		for d in employees:
			self.append('employees', d)

	def get_filter_condition(self):
		self.check_mandatory()

		cond = ''
		for f in ['company', 'branch', 'department', 'designation']:
			if self.get(f):
				cond += " and t1." + f + " = '" + self.get(f).replace("'", "\'") + "'"

		return cond

	def get_joining_releiving_condition(self):
		cond = """
			and ifnull(t1.date_of_joining, '0000-00-00') <= '%(end_date)s'
			and ifnull(t1.relieving_date, '2199-12-31') >= '%(start_date)s'
		""" % {"start_date": self.start_date, "end_date": self.end_date}
		return cond

	def check_mandatory(self):
		for fieldname in ['company', 'start_date', 'end_date']:
			if not self.get(fieldname):
				frappe.throw(_("Please set {0}").format(self.meta.get_label(fieldname)))

	def create_salary_slips(self):
		"""
			Creates salary slip for selected employees if already not created
		"""
		self.check_permission('write')
		self.created = 1;
		emp_list = self.get_emp_list()
		ss_list = []
		if emp_list:
			for emp in emp_list:
				if not frappe.db.sql("""select
						name from `tabSalary Slip`
					where
						docstatus!= 2 and
						employee = %s and
						start_date >= %s and
						end_date <= %s and
						company = %s
						""", (emp['employee'], self.start_date, self.end_date, self.company)):
					ss = frappe.get_doc({
						"doctype": "Salary Slip",
						"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
						"payroll_frequency": self.payroll_frequency,
						"start_date": self.start_date,
						"end_date": self.end_date,
						"employee": emp['employee'],
						"employee_name": frappe.get_value("Employee", {"name":emp['employee']}, "employee_name"),
						"company": self.company,
						"posting_date": self.posting_date
					})
					ss.insert()
					ss_dict = {}
					ss_dict["Employee Name"] = ss.employee_name
					ss_dict["Total Pay"] = fmt_money(ss.rounded_total,currency = frappe.defaults.get_global_default("currency"))
					ss_dict["Salary Slip"] = format_as_links(ss.name)[0]
					ss_list.append(ss_dict)
		return create_log(ss_list)

	def get_sal_slip_list(self, ss_status, as_dict=False):
		"""
			Returns list of salary slips based on selected criteria
		"""
		cond = self.get_filter_condition()

		ss_list = frappe.db.sql("""
			select t1.name, t1.salary_structure from `tabSalary Slip` t1
			where t1.docstatus = %s and t1.start_date >= %s and t1.end_date <= %s
			and (t1.journal_entry is null or t1.journal_entry = "") and ifnull(salary_slip_based_on_timesheet,0) = %s %s
		""" % ('%s', '%s', '%s','%s', cond), (ss_status, self.start_date, self.end_date, self.salary_slip_based_on_timesheet), as_dict=as_dict)
		return ss_list

	def submit_salary_slips(self):
		"""
			Submit all salary slips based on selected criteria
		"""
		self.check_permission('write')

		# self.create_salary_slips()

		jv_name = ""
		ss_list = self.get_sal_slip_list(ss_status=0)
		submitted_ss = []
		not_submitted_ss = []
		frappe.flags.via_payroll_entry = True
		for ss in ss_list:
			ss_obj = frappe.get_doc("Salary Slip",ss[0])
			ss_dict = {}
			ss_dict["Employee Name"] = ss_obj.employee_name
			ss_dict["Total Pay"] = fmt_money(ss_obj.net_pay,
				currency = frappe.defaults.get_global_default("currency"))
			ss_dict["Salary Slip"] = format_as_links(ss_obj.name)[0]

			if ss_obj.net_pay<0:
				not_submitted_ss.append(ss_dict)
			else:
				try:
					ss_obj.submit()
					submitted_ss.append(ss_obj)

				except frappe.ValidationError:
					not_submitted_ss.append(ss_dict)
		if submitted_ss:
			jv_name = self.make_accrual_jv_entry()
			frappe.msgprint(_("Salary Slip submitted for period from {0} to {1}")
				.format(ss_obj.start_date, ss_obj.end_date))

			self.email_salary_slip(submitted_ss)

		return create_submit_log(submitted_ss, not_submitted_ss, jv_name)

	def email_salary_slip(self, submitted_ss):
		if frappe.db.get_single_value("HR Settings", "email_salary_slip_to_employee"):
			for ss in submitted_ss:
				ss.email_salary_slip()

	def get_loan_details(self):
		"""
			Get loan details from submitted salary slip based on selected criteria
		"""
		cond = self.get_filter_condition()
		return frappe.db.sql(""" select eld.employee_loan_account, eld.employee_loan,
				eld.interest_income_account, eld.principal_amount, eld.interest_amount, eld.total_payment
			from
				`tabSalary Slip` t1, `tabSalary Slip Loan` eld
			where
				t1.docstatus = 1 and t1.name = eld.parent and start_date >= %s and end_date <= %s %s
			""" % ('%s', '%s', cond), (self.start_date, self.end_date), as_dict=True) or []

	def get_total_salary_amount(self):
		"""
			Get total salary amount from submitted salary slip based on selected criteria
		"""
		cond = self.get_filter_condition()
		totals = frappe.db.sql(""" select sum(rounded_total) as rounded_total from `tabSalary Slip` t1
			where t1.docstatus = 1 and start_date >= %s and end_date <= %s %s
			""" % ('%s', '%s', cond), (self.start_date, self.end_date), as_dict=True)
		return totals and totals[0] or None

	def get_salary_component_account(self, salary_component):
		account = frappe.db.get_value("Salary Component Account",
			{"parent": salary_component, "company": self.company}, "default_account")

		if not account:
			frappe.throw(_("Please set default account in Salary Component {0}")
				.format(salary_component))

		return account

	def get_salary_components(self, component_type):
		salary_slips = self.get_sal_slip_list(ss_status = 1, as_dict = True)
		if salary_slips:
			salary_components = frappe.db.sql("""select salary_component, amount, parentfield
				from `tabSalary Detail` where parentfield = '%s' and parent in (%s)""" %
				(component_type, ', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=True)
			return salary_components

	def get_salary_component_total(self, component_type = None):
		salary_components = self.get_salary_components(component_type)
		if salary_components:
			component_dict = {}
			for item in salary_components:
				component_dict[item['salary_component']] = component_dict.get(item['salary_component'], 0) + item['amount']
			account_details = self.get_account(component_dict = component_dict)
			return account_details

	def get_account(self, component_dict = None):
		account_dict = {}
		for s, a in component_dict.items():
			account = self.get_salary_component_account(s)
			account_dict[account] = account_dict.get(account, 0) + a
		return account_dict

	def get_default_payroll_payable_account(self):
		payroll_payable_account = frappe.db.get_value("Company",
			{"company_name": self.company}, "default_payroll_payable_account")

		if not payroll_payable_account:
			frappe.throw(_("Please set Default Payroll Payable Account in Company {0}")
				.format(self.company))

		return payroll_payable_account

	def make_accrual_jv_entry(self):
		self.check_permission('write')
		earnings = self.get_salary_component_total(component_type = "earnings") or {}
		deductions = self.get_salary_component_total(component_type = "deductions") or {}
		default_payroll_payable_account = self.get_default_payroll_payable_account()
		loan_details = self.get_loan_details()
		jv_name = ""
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		if earnings or deductions:
			journal_entry = frappe.new_doc('Journal Entry')
			journal_entry.voucher_type = 'Journal Entry'
			journal_entry.user_remark = _('Accrual Journal Entry for salaries from {0} to {1}')\
				.format(self.start_date, self.end_date)
			journal_entry.company = self.company
			journal_entry.posting_date = self.posting_date

			accounts = []
			payable_amount = 0

			# Earnings
			for acc, amount in earnings.items():
				payable_amount += flt(amount, precision)
				accounts.append({
						"account": acc,
						"debit_in_account_currency": flt(amount, precision),
						"cost_center": self.cost_center,
						"project": self.project
					})

			# Deductions
			for acc, amount in deductions.items():
				payable_amount -= flt(amount, precision)
				accounts.append({
						"account": acc,
						"credit_in_account_currency": flt(amount, precision),
						"cost_center": self.cost_center,
						"project": self.project
					})

			# Employee loan
			for data in loan_details:
				accounts.append({
						"account": data.employee_loan_account,
						"credit_in_account_currency": data.principal_amount
					})

				if data.interest_amount and not data.interest_income_account:
					frappe.throw(_("Select interest income account in employee loan {0}").format(data.employee_loan))

				if data.interest_income_account and data.interest_amount:
					accounts.append({
						"account": data.interest_income_account,
						"credit_in_account_currency": data.interest_amount,
						"cost_center": self.cost_center,
						"project": self.project
					})
				payable_amount -= flt(data.total_payment, precision)

			# Payable amount
			accounts.append({
				"account": default_payroll_payable_account,
				"credit_in_account_currency": flt(payable_amount, precision)
			})

			journal_entry.set("accounts", accounts)
			journal_entry.save()

			try:
				journal_entry.submit()
				jv_name = journal_entry.name
				self.update_salary_slip_status(jv_name = jv_name)
			except Exception as e:
				frappe.msgprint(e)

		return jv_name

	def make_payment_entry(self):
		self.check_permission('write')
		total_salary_amount = self.get_total_salary_amount()
		default_payroll_payable_account = self.get_default_payroll_payable_account()
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		if total_salary_amount and total_salary_amount.rounded_total:
			journal_entry = frappe.new_doc('Journal Entry')
			journal_entry.voucher_type = 'Bank Entry'
			journal_entry.user_remark = _('Payment of salary from {0} to {1}')\
				.format(self.start_date, self.end_date)
			journal_entry.company = self.company
			journal_entry.posting_date = self.posting_date

			payment_amount = flt(total_salary_amount.rounded_total, precision)

			journal_entry.set("accounts", [
				{
					"account": self.payment_account,
					"credit_in_account_currency": payment_amount
				},
				{
					"account": default_payroll_payable_account,
					"debit_in_account_currency": payment_amount,
					"reference_type": self.doctype,
					"reference_name": self.name
				}
			])
			return journal_entry.as_dict()
		else:
			frappe.msgprint(
				_("There are no submitted Salary Slips to process."),
				title="Error", indicator="red"
			)

	def update_salary_slip_status(self, jv_name = None):
		ss_list = self.get_sal_slip_list(ss_status=1)
		for ss in ss_list:
			ss_obj = frappe.get_doc("Salary Slip",ss[0])
			frappe.db.set_value("Salary Slip", ss_obj.name, "status", "Paid")
			frappe.db.set_value("Salary Slip", ss_obj.name, "journal_entry", jv_name)

	def set_start_end_dates(self):
		self.update(get_start_end_dates(self.payroll_frequency,
			self.start_date or self.posting_date, self.company))


@frappe.whitelist()
def get_start_end_dates(payroll_frequency, start_date=None, company=None):
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


def get_frequency_kwargs(frequency_name):
	frequency_dict = {
		'monthly': {'months': 1},
		'fortnightly': {'days': 14},
		'weekly': {'days': 7},
		'daily': {'days': 1}
	}
	return frequency_dict.get(frequency_name)


@frappe.whitelist()
def get_end_date(start_date, frequency):
	start_date = getdate(start_date)
	frequency = frequency.lower() if frequency else 'monthly'
	kwargs = get_frequency_kwargs(frequency) if frequency != 'bimonthly' else get_frequency_kwargs('monthly')

	# weekly, fortnightly and daily intervals have fixed days so no problems
	end_date = add_to_date(start_date, **kwargs) - relativedelta(days=1)
	if frequency != 'bimonthly':
		return dict(end_date=end_date.strftime(DATE_FORMAT))

	else:
		return dict(end_date='')


def get_month_details(year, month):
	ysd = frappe.db.get_value("Fiscal Year", year, "year_start_date")
	if ysd:
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


@frappe.whitelist()
def create_log(ss_list):
	if not ss_list:
		frappe.throw(
			_("There's no employee for the given criteria. Check that Salary Slips have not already been created."),
			title='Error'
		)
	return ss_list


def format_as_links(salary_slip):
	return ['<a href="#Form/Salary Slip/{0}">{0}</a>'.format(salary_slip)]


def create_submit_log(submitted_ss, not_submitted_ss, jv_name):

	if not submitted_ss and not not_submitted_ss:
		frappe.msgprint("No salary slip found to submit for the above selected criteria OR salary slip already submitted")

	if not_submitted_ss:
		frappe.msgprint("Could not submit any Salary Slip <br>\
			Possible reasons: <br>\
			1. Net pay is less than 0. <br>\
			2. Company Email Address specified in employee master is not valid. <br>")


def get_salary_slip_list(name, docstatus, as_dict=0):
	payroll_entry = frappe.get_doc('Payroll Entry', name)

	salary_slip_list = frappe.db.sql(
		"select t1.name, t1.salary_structure from `tabSalary Slip` t1 "
		"where t1.docstatus = %s "
		"and t1.start_date >= %s "
		"and t1.end_date <= %s",
		(docstatus, payroll_entry.start_date, payroll_entry.end_date),
		as_dict=as_dict
	)

	return salary_slip_list


@frappe.whitelist()
def payroll_entry_has_created_slips(name):
	response = {}

	draft_salary_slips = get_salary_slip_list(name, docstatus=0)
	submitted_salary_slips = get_salary_slip_list(name, docstatus=1)

	response['draft'] = 1 if draft_salary_slips else 0
	response['submitted'] = 1 if submitted_salary_slips else 0

	return response


def get_payroll_entry_bank_entries(payroll_entry_name):
	journal_entries = frappe.db.sql(
		'select name from `tabJournal Entry Account` '
		'where reference_type="Payroll Entry" '
		'and reference_name=%s and docstatus=1',
		payroll_entry_name,
		as_dict=1
	)

	return journal_entries


@frappe.whitelist()
def payroll_entry_has_bank_entries(name):
	response = {}

	bank_entries = get_payroll_entry_bank_entries(name)
	response['submitted'] = 1 if bank_entries else 0

	return response

def get_payroll_entries_for_jv(doctype, txt, searchfield, start, page_len, filters):
	print(doctype)
	return frappe.db.sql("""
		select name from `tabPayroll Entry`
		where `{key}` LIKE %(txt)s
		and name not in
			(select reference_name from `tabJournal Entry Account`
				where reference_type="Payroll Entry")
		order by name limit %(start)s, %(page_len)s"""
		.format(key=searchfield), {
			'txt': "%%%s%%" % frappe.db.escape(txt),
			'start': start, 'page_len': page_len
		})
