# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, flt, nowdate, add_days, getdate, fmt_money, add_to_date, DATE_FORMAT, date_diff
from frappe import _
from erpnext.accounts.utils import get_fiscal_year
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center

class PayrollEntry(Document):
	def onload(self):
		if self.docstatus != 1:
			return

		if not self.salary_slips_submitted:
			# check if salary slips were manually submitted
			entries = frappe.db.count("Salary Slip", {'payroll_entry': self.name, 'docstatus': 1})
			if cint(entries) == len(self.employees):
				self.set_onload("submitted_ss", True)

		self.set_onload('has_bank_entries', self.payroll_entry_has_bank_entries())

	def on_submit(self):
		self.create_salary_slips()

	def before_submit(self):
		if self.validate_attendance:
			if self.validate_employee_attendance():
				frappe.throw(_("Cannot Submit, Employees left to mark attendance"))
				
	def before_print(self):
		bank_details = self.get_bank_details()
		self.bank_details = bank_details

	def on_cancel(self):
		ss = frappe.db.sql("""select name, journal_entry from `tabSalary Slip`
			where payroll_entry=%s""", (self.name), as_dict=1)

		salary_slips = [d.name for d in ss]
		journal_entries = list(set([d.journal_entry for d in ss if d.journal_entry]))

		frappe.delete_doc("Salary Slip", salary_slips)
		for jv in journal_entries:
			frappe.get_doc("Journal Entry", jv).cancel()

	def get_emp_list(self):
		"""
			Returns list of active employees based on selected criteria
			and for which salary structure exists
		"""
		cond = self.get_filter_condition()
		cond += self.get_joining_relieving_condition()

		condition = ''
		if self.payroll_frequency:
			condition = """and payroll_frequency = '%(payroll_frequency)s'"""% {"payroll_frequency": self.payroll_frequency}

		sal_struct = frappe.db.sql_list("""
				select
					name from `tabSalary Structure`
				where
					docstatus = 1 and
					is_active = 'Yes'
					and company = %(company)s and
					ifnull(salary_slip_based_on_timesheet,0) = %(salary_slip_based_on_timesheet)s
					{condition}""".format(condition=condition),
				{"company": self.company, "salary_slip_based_on_timesheet":self.salary_slip_based_on_timesheet})
		if sal_struct:
			cond += "and t2.salary_structure IN %(sal_struct)s "
			cond += "and %(from_date)s >= t2.from_date"
			emp_list = frappe.db.sql("""
				select
					distinct t1.name as employee, t1.employee_name, t1.department, t1.designation
				from
					`tabEmployee` t1, `tabSalary Structure Assignment` t2
				where
					t1.name = t2.employee
					and t2.docstatus = 1
			%s order by t2.from_date desc
			""" % cond, {"sal_struct": tuple(sal_struct), "from_date": self.end_date}, as_dict=True)
			return emp_list

	def fill_employee_details(self):
		self.set('employees', [])
		employees = self.get_emp_list()
		if not employees:
			frappe.throw(_("No employees for the mentioned criteria"))

		for d in employees:
			self.append('employees', d)

		self.number_of_employees = len(employees)
		if self.validate_attendance:
			return self.validate_employee_attendance()

	def get_filter_condition(self):
		self.check_mandatory()

		cond = ''
		for f in ['company', 'branch', 'department', 'designation']:
			if self.get(f):
				cond += " and t1." + f + " = '" + self.get(f).replace("'", "\'") + "'"

		return cond

	def get_joining_relieving_condition(self):
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
		self.created = 1
		emp_list = [d.employee for d in self.get_emp_list()]
		if emp_list:
			args = frappe._dict({
				"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
				"payroll_frequency": self.payroll_frequency,
				"start_date": self.start_date,
				"end_date": self.end_date,
				"company": self.company,
				"posting_date": self.posting_date,
				"deduct_tax_for_unclaimed_employee_benefits": self.deduct_tax_for_unclaimed_employee_benefits,
				"deduct_tax_for_unsubmitted_tax_exemption_proof": self.deduct_tax_for_unsubmitted_tax_exemption_proof,
				"payroll_entry": self.name
			})
			if len(emp_list) > 30:
				self.queue_action('_create_salary_slips_for_employees', timeout=600, employees=emp_list, args=args)
			else:
				self._create_salary_slips_for_employees(emp_list, args, publish_progress=False)
				# since this method is called via frm.call this doc needs to be updated manually
				self.reload()

	def _create_salary_slips_for_employees(self, employees, args, publish_progress=True):

		salary_slips_exists_for = frappe.db.sql_list("""
		select distinct employee from `tabSalary Slip`
		where docstatus != 2 and company = %s
			and start_date >= %s and end_date <= %s
			and employee in (%s)
	""" % ('%s', '%s', '%s', ', '.join(['%s']*len(employees))),
		[args.company, args.start_date, args.end_date] + employees)

		self.check_permission('write')
		for count, emp in enumerate(employees):
			if emp not in salary_slips_exists_for:
				args.update({
					"doctype": "Salary Slip",
					"employee": emp
				})
				ss = frappe.get_doc(args)
				ss.insert()

			if publish_progress:
				frappe.publish_progress((count + 1) * 100 / len(employees), title=_("Creating Salary Slips..."))

		self.db_set("salary_slips_created", 1)
		self.notify_update()

	def update_salary_slips(self):
		"""
			Creates salary slip for selected employees if already not created
		"""
		self.check_permission('write')
		ss_list = self.get_sal_slip_list(0, as_dict=True)

		if ss_list:
			if len(ss_list) > 30:
				self.queue_action('_update_salary_slips', timeout=600, sal_slips=ss_list)
			else:
				self._update_salary_slips(ss_list, publish_progress=False)
				frappe.msgprint(_("Updated Salary Slips Successfully"))

	def _update_salary_slips(self, sal_slips, publish_progress=True):
		self.check_permission('write')
		for count, ss in enumerate(sal_slips):
			doc = frappe.get_doc("Salary Slip", ss.name)
			doc.leave_without_pay = 0
			doc.save()
			if publish_progress:
				frappe.publish_progress((count + 1) * 100 / len(sal_slips), title=_("Updating Salary Slips..."))

	def get_sal_slip_list(self, ss_status, as_dict=False):
		"""
			Returns list of salary slips based on selected criteria
		"""
		cond = self.get_filter_condition()

		ss_list = frappe.db.sql("""
			select t1.name, t1.salary_structure, t1.rounded_total from `tabSalary Slip` t1
			where t1.docstatus = %s and t1.start_date >= %s and t1.end_date <= %s
			and (t1.journal_entry is null or t1.journal_entry = "") and ifnull(salary_slip_based_on_timesheet,0) = %s %s
		""" % ('%s', '%s', '%s','%s', cond), (ss_status, self.start_date, self.end_date, self.salary_slip_based_on_timesheet), as_dict=as_dict)
		return ss_list

	def submit_salary_slips(self):
		self.check_permission('write')
		ss_list = self.get_sal_slip_list(0, as_dict=True)
		if len(ss_list) > 30:
			self.queue_action('_submit_salary_slips', timeout=600, sal_slips=ss_list)
		else:
			self._submit_salary_slips(ss_list, publish_progress=False)

	def _submit_salary_slips(self, sal_slips, publish_progress=True):
		self.check_permission('write')
		submitted_ss = []
		not_submitted_ss = []
		frappe.flags.via_payroll_entry = True

		for count, ss in enumerate(sal_slips):
			ss_obj = frappe.get_doc("Salary Slip", ss.name)
			if ss_obj.net_pay < 0:
				not_submitted_ss.append(ss.name)
			else:
				ss_obj.submit()
				submitted_ss.append(ss_obj)

			if publish_progress:
				frappe.publish_progress((count + 1) * 100 / len(sal_slips), title=_("Submitting Salary Slips..."))

		self.make_accrual_jv_entry()
		if submitted_ss:
			self.email_salary_slip(submitted_ss)

			frappe.msgprint(_("Salary Slips submitted for period from {0} to {1}")
				.format(self.get_formatted('start_date'), self.get_formatted('end_date')))

		self.db_set("salary_slips_submitted", 1)
		self.notify_update()

		if not submitted_ss and not not_submitted_ss:
			frappe.msgprint(
				_("No Salary Slips found to submit for the above selected criteria OR salary slip already submitted"))

		if not_submitted_ss:
			frappe.msgprint(_("Could not submit some Salary Slips"))

	def email_salary_slip(self, submitted_ss):
		if frappe.db.get_single_value("HR Settings", "email_salary_slip_to_employee"):
			for ss in submitted_ss:
				ss.email_salary_slip()

	def get_loan_details(self):
		"""
			Get loan details from submitted salary slip based on selected criteria
		"""
		cond = self.get_filter_condition()
		return frappe.db.sql(""" select eld.loan_account, eld.loan,
				eld.interest_income_account, eld.principal_amount, eld.interest_amount, eld.total_payment,t1.employee
			from
				`tabSalary Slip` t1, `tabSalary Slip Loan` eld
			where
				t1.docstatus = 1 and t1.name = eld.parent and start_date >= %s and end_date <= %s %s
			""" % ('%s', '%s', cond), (self.start_date, self.end_date), as_dict=True) or []

	def get_advance_details(self):
		"""
			Get advance details from submitted salary slip based on selected criteria
		"""

		cond = self.get_filter_condition()
		return frappe.db.sql("""
			select t1.employee, ead.employee_advance,  ead.advance_account, ead.balance_amount, ead.allocated_amount
			from 
				`tabSalary Slip` t1, `tabSalary Slip Employee Advance` ead
			where
				t1.docstatus = 1 and t1.name = ead.parent and  start_date >= %s and end_date <= %s %s
			""" % ('%s', '%s', cond), (self.start_date, self.end_date), as_dict=True) or []

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
				from `tabSalary Detail`
				where parentfield = '%s' and parent in (%s)""" %
				(component_type, ', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=True)
			return salary_components

	def get_salary_component_total(self, component_type = None):
		salary_components = self.get_salary_components(component_type)
		if salary_components:
			component_dict = {}
			for item in salary_components:
				add_component_to_accrual_jv_entry = True
				if component_type == "earnings":
					is_flexible_benefit, only_tax_impact = frappe.db.get_value("Salary Component", item['salary_component'], ['is_flexible_benefit', 'only_tax_impact'])
					if is_flexible_benefit == 1 and only_tax_impact ==1:
						add_component_to_accrual_jv_entry = False
				if add_component_to_accrual_jv_entry:
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
		payroll_payable_account = frappe.get_cached_value('Company',
			{"company_name": self.company},  "default_payroll_payable_account")

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
		advance_details = self.get_advance_details()
		jv_name = ""
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
		round_off_account, round_off_cost_center = get_round_off_account_and_cost_center(self.company)

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
						"party_type": '',
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
						"party_type": '',
						"project": self.project
					})

			# Loan
			for data in loan_details:
				accounts.append({
						"account": data.loan_account,
						"credit_in_account_currency": data.principal_amount,
						"party_type": "Employee",
						"party": data.employee
					})

				if data.interest_amount and not data.interest_income_account:
					frappe.throw(_("Select interest income account in loan {0}").format(data.loan))

				if data.interest_income_account and data.interest_amount:
					accounts.append({
						"account": data.interest_income_account,
						"credit_in_account_currency": data.interest_amount,
						"cost_center": self.cost_center,
						"project": self.project,
						"party_type": "Employee",
						"party": data.employee
					})
				payable_amount -= flt(data.total_payment, precision)

			for data in advance_details:
				allocated_amount = flt(data.allocated_amount, precision)
				payable_amount -= allocated_amount

				if allocated_amount:
					accounts.append({
						"account": data.advance_account,
						"party": data.employee,
						"party_type": "Employee",
						"reference_type": "Employee Advance",
						"credit_in_account_currency": allocated_amount,
						"reference_name": data.employee_advance,
						"cost_center": self.cost_center
					})

			payable_amount_rounded = 0
			ss_list = self.get_sal_slip_list(ss_status=1, as_dict=1)
			for ss in ss_list:
				payable_amount_rounded += ss.rounded_total

			payable_amount_rounded = flt(payable_amount_rounded, precision)
			payable_amount = flt(payable_amount, precision)
			round_off_amount = flt(payable_amount_rounded - payable_amount, precision)

			accounts.append({
				"account": default_payroll_payable_account,
				"credit_in_account_currency": payable_amount_rounded if round_off_amount else payable_amount,
				"party_type": '',
				"cost_center": self.cost_center
			})

			if round_off_amount:
				accounts.append({
					"account": round_off_account,
					"debit_in_account_currency": round_off_amount if round_off_amount > 0 else 0,
					"credit_in_account_currency": abs(round_off_amount) if round_off_amount < 0 else 0,
					"cost_center": self.cost_center or round_off_cost_center,
				})

			journal_entry.set("accounts", accounts)
			journal_entry.title = default_payroll_payable_account
			journal_entry.save()

			jv_name = journal_entry.name
			self.update_salary_slip_status(jv_name = jv_name)

			journal_entry.submit()

		return jv_name

	def payroll_entry_has_bank_entries(self):

		journal_entries_amount_sum = frappe.db.sql(
			'select sum(debit-credit) as amount_sum from `tabJournal Entry Account` '
			'where reference_type="Payroll Entry" '
			'and reference_name=%s and docstatus=1', self.name, as_list=True
		)

		journal_entries_amount_sum = flt(journal_entries_amount_sum[0][0]) if journal_entries_amount_sum else 0
		salary_slips = self.get_salary_slips_for_payment()

		ss_rounded_total_sums = sum([ss.rounded_total for ss in salary_slips])

		return 0 if journal_entries_amount_sum < ss_rounded_total_sums else 1

	def get_salary_slips_for_payment(self, include_draft=False):
		docstatus_cond = "t1.docstatus < 2" if include_draft else "t1.docstatus = 1"
		filter_cond = self.get_filter_condition()

		salary_slips = frappe.db.sql("""
			select t1.name, t1.employee, t1.employee_name, t1.salary_mode, t1.bank_name, t1.bank_account_no, t1.net_pay, t1.rounded_total
			from `tabSalary Slip` t1
			where {0} and start_date >= %s and end_date <= %s {1}
		""".format(docstatus_cond, filter_cond), (self.start_date, self.end_date), as_dict=True)

		return salary_slips

	def get_disbursement_mode_details(self):
		salary_slips = self.get_salary_slips_for_payment()
		salary_modes = set([ss.salary_mode for ss in salary_slips if ss.salary_mode and ss.salary_mode != "Cheque"])
		bank_names = set([ss.bank_name for ss in salary_slips if ss.salary_mode == 'Bank' and ss.bank_name])

		return list(salary_modes), list(bank_names)

	def get_bank_details(self):
		sal_slips_in_payroll = self.get_salary_slips_for_payment(include_draft=True)
		sal_slips_in_payroll = [d for d in sal_slips_in_payroll if d.salary_mode == 'Bank' and d.bank_name]

		bank_employee_map = {}
		for d in sal_slips_in_payroll:
			bank_name = d.bank_name
			bank_employee_map.setdefault(bank_name, frappe._dict({'employees': [], 'total': 0}))

			bank_employee_map[bank_name].employees.append({
				'employee': d.employee,
				'employee_name': d.employee_name,
				'rounded_total': d.rounded_total,
				'bank_account_no': d.bank_account_no
			})
			bank_employee_map[bank_name].total += d.rounded_total

		return bank_employee_map

	def make_payment_entry(self, payment_account, salary_mode=None, bank_name=None):
		from erpnext.accounts.utils import get_currency_precision

		self.check_permission('write')
		self.payment_account = payment_account

		salary_slips = self.get_salary_slips_for_payment()
		if salary_mode:
			salary_slips = [d for d in salary_slips if d.salary_mode == salary_mode]
		if salary_mode == "Bank" and bank_name:
			salary_slips = [d for d in salary_slips if d.bank_name == bank_name]

		jv_names = []
		salary_slip_total = 0
		separate_jv_amount = 0
		if salary_slips:
			for ss in salary_slips:
				salary_slip = frappe.get_doc("Salary Slip", ss.name)
				salary_slip_total += salary_slip.rounded_total
				for sal_detail in salary_slip.earnings:
					is_flexible_benefit, only_tax_impact, creat_separate_je, statistical_component = frappe.db.get_value("Salary Component", sal_detail.salary_component,
						['is_flexible_benefit', 'only_tax_impact', 'create_separate_payment_entry_against_benefit_claim', 'statistical_component'])

					if only_tax_impact != 1 and statistical_component != 1:
						if is_flexible_benefit == 1 and creat_separate_je == 1:
							jv_names.append(self.create_journal_entry(sal_detail.amount, sal_detail.salary_component))
							separate_jv_amount += sal_detail.amount

			currency_precision = get_currency_precision() or 2
			salary_slip_total = flt(salary_slip_total - separate_jv_amount, currency_precision)

			if salary_slip_total > 0:
				jv_names.append(self.create_journal_entry(salary_slip_total, "salary"))

		return jv_names

	def create_journal_entry(self, je_payment_amount, user_remark):
		default_payroll_payable_account = self.get_default_payroll_payable_account()
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = 'Bank Entry'
		journal_entry.user_remark = _('Payment of {0} from {1} to {2}')\
			.format(user_remark, self.start_date, self.end_date)
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date

		payment_amount = flt(je_payment_amount, precision)

		journal_entry.set("accounts", [
			{
				"account": default_payroll_payable_account,
				"debit_in_account_currency": payment_amount,
				"reference_type": self.doctype,
				"reference_name": self.name
			},
			{
				"account": self.payment_account,
				"bank_account": self.bank_account,
				"credit_in_account_currency": payment_amount
			}
		])
		journal_entry.save(ignore_permissions=True)

		return journal_entry.name

	def update_salary_slip_status(self, jv_name = None):
		ss_list = self.get_sal_slip_list(ss_status=1, as_dict=1)
		for ss in ss_list:
			frappe.db.set_value("Salary Slip", ss.name, "journal_entry", jv_name)

	def set_start_end_dates(self):
		self.update(get_start_end_dates(self.payroll_frequency,
			self.start_date or self.posting_date, self.company))

	def validate_employee_attendance(self):
		employees_to_mark_attendance = []
		days_in_payroll, days_holiday, days_attendance_marked = 0, 0, 0
		for employee_detail in self.employees:
			days_holiday = self.get_count_holidays_of_employee(employee_detail.employee)
			days_attendance_marked = self.get_count_employee_attendance(employee_detail.employee)
			days_in_payroll = date_diff(self.end_date, self.start_date) + 1
			if days_in_payroll > days_holiday + days_attendance_marked:
				employees_to_mark_attendance.append({
					"employee": employee_detail.employee,
					"employee_name": employee_detail.employee_name
					})
		return employees_to_mark_attendance

	def get_count_holidays_of_employee(self, employee):
		holiday_list = get_holiday_list_for_employee(employee)
		holidays = 0
		if holiday_list:
			days = frappe.db.sql("""select count(*) from tabHoliday where
				parent=%s and holiday_date between %s and %s""", (holiday_list,
				self.start_date, self.end_date))
			if days and days[0][0]:
				holidays = days[0][0]
		return holidays

	def get_count_employee_attendance(self, employee):
		marked_days = 0
		attendances = frappe.db.sql("""select count(*) from tabAttendance where
			employee=%s and docstatus=1 and attendance_date between %s and %s""",
			(employee, self.start_date, self.end_date))
		if attendances and attendances[0][0]:
			marked_days = attendances[0][0]
		return marked_days

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
@frappe.validate_and_sanitize_search_inputs
def get_payroll_entries_for_jv(doctype, txt, searchfield, start, page_len, filters):
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