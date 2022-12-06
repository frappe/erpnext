# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, flt, add_days, getdate, add_to_date, DATE_FORMAT, date_diff, formatdate
from frappe import _, scrub
from erpnext.accounts.utils import get_fiscal_year
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center
from erpnext.accounts.utils import get_allow_cost_center_in_entry_of_bs_account


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

	def before_print(self):
		bank_details = self.get_bank_details()
		self.bank_details = bank_details

	def before_submit(self):
		if self.validate_attendance:
			if self.validate_employee_attendance():
				frappe.throw(_("Cannot Submit, Employees left to mark attendance"))

	def on_submit(self):
		self.create_salary_slips()

	def on_cancel(self):
		ss = frappe.db.sql("""
			select name, journal_entry, docstatus
			from `tabSalary Slip`
			where payroll_entry = %s
		""", self.name, as_dict=1)

		submitted_salary_slips = [d.name for d in ss if d.docstatus == 1]
		draft_salary_slips = [d.name for d in ss if d.docstatus == 0]

		journal_entries = list(set([d.journal_entry for d in ss if d.journal_entry]))

		for name in submitted_salary_slips:
			frappe.get_doc("Salary Slip", name).cancel()

		if draft_salary_slips:
			frappe.delete_doc("Salary Slip", draft_salary_slips)

		for jv in journal_entries:
			doc = frappe.get_doc("Journal Entry", jv)
			if doc.docstatus == 1:
				doc.cancel()

	def on_trash(self):
		ss = frappe.db.sql("""
			select name, journal_entry, docstatus
			from `tabSalary Slip`
			where payroll_entry = %s
		""", self.name, as_dict=1)

		salary_slips = [d.name for d in ss]
		journal_entries = list(set([d.journal_entry for d in ss if d.journal_entry]))

		if salary_slips:
			frappe.delete_doc("Salary Slip", salary_slips)

		if journal_entries:
			frappe.delete_doc("Journal Entry", journal_entries)

	def get_employees(self):
		"""
			Returns list of active employees based on selected criteria
			and for which salary structure exists
		"""
		structure_condition = ""
		if self.payroll_frequency:
			structure_condition = "and payroll_frequency = {0}".format(frappe.db.escape(self.payroll_frequency))

		salary_structures = frappe.db.sql_list("""
			select distinct name
			from `tabSalary Structure`
			where docstatus = 1
				and is_active = 'Yes'
				and company = %(company)s
				and ifnull(salary_slip_based_on_timesheet, 0) = %(salary_slip_based_on_timesheet)s
				{0}
		""".format(structure_condition), {
			"company": self.company,
			"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet
		})

		if salary_structures:
			employee_condition = self.get_filter_condition(prefix="emp")
			employee_condition += self.get_joining_relieving_condition()
			employee_condition += " and ssa.salary_structure IN %(salary_structures)s "
			employee_condition += " and ssa.from_date <= %(end_date)s"

			employees = frappe.db.sql("""
				select distinct emp.name as employee, emp.employee_name, emp.department, emp.designation
				from `tabEmployee` emp, `tabSalary Structure Assignment` ssa
				where emp.name = ssa.employee and ssa.docstatus = 1 {0}
				order by ssa.from_date desc
			""".format(employee_condition), {
				"salary_structures": tuple(salary_structures),
				"end_date": self.end_date
			}, as_dict=True)

			return employees

	def fill_employee_details(self):
		self.set('employees', [])

		employees = self.get_employees()
		if not employees:
			frappe.throw(_("No Employees for the mentioned criteria"))

		for d in employees:
			self.append('employees', d)

		self.number_of_employees = len(employees)

		if self.validate_attendance:
			return self.validate_employee_attendance()

	def get_filter_condition(self, prefix="ss"):
		self.check_mandatory()

		cond = ""
		for f in ['company', 'branch', 'department', 'designation']:
			if self.get(f):
				cond += " and {prefix}.{field} = {value}"\
					.format(prefix=prefix, field=f, value=frappe.db.escape(self.get(f)))

		return cond

	def get_joining_relieving_condition(self):
		cond = """
			and ifnull(emp.date_of_joining, '0000-00-00') <= '%(end_date)s'
			and ifnull(emp.relieving_date, '2199-12-31') >= '%(start_date)s'
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

		employees = [d.employee for d in self.get_employees()]
		if employees:
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
			if len(employees) > 30:
				self.queue_action('_create_salary_slips_for_employees', timeout=600, employees=employees, args=args)
			else:
				self._create_salary_slips_for_employees(employees, args, publish_progress=False)
				# since this method is called via frm.call this doc needs to be updated manually
				self.reload()

	def _create_salary_slips_for_employees(self, employees, args, publish_progress=True):
		self.check_permission('write')

		employees_with_existing_salary_slips = []
		if employees:
			employees_with_existing_salary_slips = frappe.db.sql_list("""
				select distinct employee
				from `tabSalary Slip`
				where docstatus < 2 and company = %s
					and start_date >= %s and end_date <= %s
					and employee in %s
		""", (args.company, args.start_date, args.end_date, employees))

		for count, employee in enumerate(employees):
			if employee not in employees_with_existing_salary_slips:
				args.update({
					"doctype": "Salary Slip",
					"employee": employee
				})
				salary_slip = frappe.get_doc(args)
				salary_slip.flags.from_payroll_entry = True
				salary_slip.insert()

			if publish_progress:
				frappe.publish_progress((count + 1) * 100 / len(employees), title=_("Creating Salary Slips..."))

		self.db_set("salary_slips_created", 1)
		self.notify_update()

	def update_salary_slips(self):
		"""
			Creates salary slip for selected employees if already not created
		"""
		self.check_permission('write')

		salary_slips = self.get_salary_slips(0, as_dict=True)
		if salary_slips:
			if len(salary_slips) > 30:
				self.queue_action('_update_salary_slips', timeout=600, salary_slips=salary_slips)
			else:
				self._update_salary_slips(salary_slips, publish_progress=False)
				frappe.msgprint(_("Updated Salary Slips Successfully"))

	def _update_salary_slips(self, salary_slips, publish_progress=True):
		self.check_permission('write')
		for count, ss in enumerate(salary_slips):
			doc = frappe.get_doc("Salary Slip", ss.name)
			doc.flags.from_payroll_entry = True
			doc.save()
			if publish_progress:
				frappe.publish_progress((count + 1) * 100 / len(salary_slips), title=_("Updating Salary Slips..."))

	def get_salary_slips(self, ss_status, as_dict=False):
		"""
			Returns list of salary slips based on selected criteria
		"""
		cond = self.get_filter_condition()

		salary_slips = frappe.db.sql("""
			select ss.name, ss.salary_structure, ss.rounded_total
			from `tabSalary Slip` ss
			where ss.docstatus = %s
				and ss.start_date >= %s and ss.end_date <= %s
				and (ss.journal_entry is null or ss.journal_entry = '')
				and ifnull(salary_slip_based_on_timesheet, 0) = %s
				{0}
		""".format(cond), (ss_status, self.start_date, self.end_date, self.salary_slip_based_on_timesheet), as_dict=as_dict)

		return salary_slips

	def submit_salary_slips(self):
		self.check_permission('write')
		salary_slips = self.get_salary_slips(0, as_dict=True)
		if len(salary_slips) > 30:
			self.queue_action('_submit_salary_slips', timeout=600, salary_slips=salary_slips)
		else:
			self._submit_salary_slips(salary_slips, publish_progress=False)

	def _submit_salary_slips(self, salary_slips, publish_progress=True):
		self.check_permission('write')
		submitted_ss = []
		not_submitted_ss = []
		frappe.flags.via_payroll_entry = True

		for count, ss in enumerate(salary_slips):
			ss_obj = frappe.get_doc("Salary Slip", ss.name)
			ss_obj.flags.from_payroll_entry = True
			if ss_obj.net_pay < 0:
				not_submitted_ss.append(ss.name)
			else:
				ss_obj.submit()
				submitted_ss.append(ss_obj)

			if publish_progress:
				frappe.publish_progress((count + 1) * 100 / len(salary_slips), title=_("Submitting Salary Slips..."))

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
		conditions = self.get_filter_condition()
		return frappe.db.sql("""
			select ss.employee, eld.loan, eld.loan_account, eld.interest_income_account,
				eld.principal_amount, eld.interest_amount, eld.total_payment
			from `tabSalary Slip` ss, `tabSalary Slip Loan` eld
			where ss.name = eld.parent and ss.docstatus = 1 and ss.start_date >= %s and ss.end_date <= %s {0}
		""".format(conditions), (self.start_date, self.end_date), as_dict=True) or []

	def get_advance_details(self):
		"""
			Get advance details from submitted salary slip based on selected criteria
		"""

		conditions = self.get_filter_condition()
		return frappe.db.sql("""
			select ss.employee, ead.employee_advance,  ead.advance_account, ead.balance_amount, ead.allocated_amount
			from `tabSalary Slip` ss, `tabSalary Slip Employee Advance` ead
			where ss.name = ead.parent and ss.docstatus = 1 and ss.start_date >= %s and ss.end_date <= %s {0}
			""".format(conditions), (self.start_date, self.end_date), as_dict=True) or []

	def get_salary_component_account(self, salary_component):
		if self.get('_salary_component_account_map') and self._salary_component_account_map.get(salary_component):
			account = self._salary_component_account_map.get(salary_component)
		else:
			account = frappe.db.get_value("Salary Component Account",
				{"parent": salary_component, "company": self.company}, "default_account", cache=1)

			if not account:
				frappe.throw(_("Please set default account in Salary Component {0}")
					.format(salary_component))

			if not self.get('_salary_component_account_map'):
				self._salary_component_account_map = {}

			self._salary_component_account_map[salary_component] = account

		return account

	def get_salary_components(self, component_type):
		salary_slips = self.get_salary_slips(ss_status=1, as_dict=True)
		salary_slip_names = [d.name for d in salary_slips]
		if salary_slip_names:
			salary_components = frappe.db.sql("""
				select sc.salary_component, sc.amount, sc.parentfield, ss.cost_center
				from `tabSalary Detail` sc
				left join `tabSalary Slip` ss on ss.name = sc.parent
				where sc.parentfield = %s and sc.parent in %s and sc.do_not_include_in_total = 0
			""", (component_type, salary_slip_names), as_dict=True)
			return salary_components

	def get_salary_component_total(self, component_type=None):
		salary_components = self.get_salary_components(component_type)
		if salary_components:
			component_map = {}
			for item in salary_components:
				add_component_to_accrual_jv_entry = True

				if component_type == "earnings":
					component_details = frappe.db.get_value("Salary Component", item['salary_component'],
						('is_flexible_benefit', 'only_tax_impact'), as_dict=1, cache=1)

					if component_details.is_flexible_benefit and component_details.only_tax_impact:
						add_component_to_accrual_jv_entry = False

				if add_component_to_accrual_jv_entry:
					component = item['salary_component']
					component_account = self.get_salary_component_account(component)
					account_report_type = frappe.db.get_value("Account", component_account, "report_type", cache=1)

					if account_report_type == "Profit and Loss" or get_allow_cost_center_in_entry_of_bs_account():
						cost_center = item['cost_center'] or self.get("cost_center") or ""
					else:
						cost_center = ""

					component_map.setdefault(component, {}).setdefault(cost_center, 0)
					component_map[component][cost_center] += item['amount']

			return component_map

	def get_default_payroll_payable_account(self):
		payroll_payable_account = frappe.get_cached_value('Company',
			{"company_name": self.company},  "default_payroll_payable_account")

		if not payroll_payable_account:
			frappe.throw(_("Please set Default Payroll Payable Account in Company {0}")
				.format(self.company))

		return payroll_payable_account

	def make_accrual_jv_entry(self):
		self.check_permission('write')

		earnings = self.get_salary_component_total(component_type="earnings") or {}
		deductions = self.get_salary_component_total(component_type="deductions") or {}
		loan_details = self.get_loan_details()
		advance_details = self.get_advance_details()
		payroll_payable_account = self.get_default_payroll_payable_account()
		round_off_account, round_off_cost_center = get_round_off_account_and_cost_center(self.company)
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		jv_name = None

		if earnings or deductions:
			journal_entry = frappe.new_doc('Journal Entry')
			journal_entry.voucher_type = 'Journal Entry'
			journal_entry.company = self.company
			journal_entry.posting_date = self.posting_date

			journal_entry.user_remark = _('Accrual Journal Entry for salaries from {0} to {1}')\
				.format(self.get_formatted("start_date"), self.get_formatted("end_date"))

			accounts = []
			payable_amount = 0

			# Earnings
			for component, component_cost_centers in earnings.items():
				account = self.get_salary_component_account(component)

				for cost_center, amount in component_cost_centers.items():
					payable_amount += flt(amount, precision)
					accounts.append({
						"account": account,
						"debit_in_account_currency": flt(amount, precision),
						"cost_center": cost_center or self.cost_center,
						"project": self.project,
						"user_remark": _("{0} Salary Component").format(component),
					})

			# Deductions
			for component, component_cost_centers in deductions.items():
				account = self.get_salary_component_account(component)

				for cost_center, amount in component_cost_centers.items():
					payable_amount -= flt(amount, precision)
					accounts.append({
						"account": account,
						"credit_in_account_currency": flt(amount, precision),
						"cost_center": cost_center or self.cost_center,
						"project": self.project,
						"user_remark": _("{0} Salary Component").format(component),
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

			payable_amount = flt(payable_amount, precision)

			salary_slips = self.get_salary_slips(ss_status=1, as_dict=True)
			payable_amount_rounded = sum([ss.rounded_total for ss in salary_slips])
			payable_amount_rounded = flt(payable_amount_rounded, precision)

			round_off_amount = flt(payable_amount_rounded - payable_amount, precision)

			accounts.append({
				"account": payroll_payable_account,
				"credit_in_account_currency": payable_amount_rounded if round_off_amount else payable_amount,
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
			journal_entry.title = payroll_payable_account
			journal_entry.save()

			jv_name = journal_entry.name
			self.update_salary_slip_status(jv_name=jv_name)

			journal_entry.submit()

		return jv_name

	def payroll_entry_has_bank_entries(self):
		journal_entries_amount_sum = frappe.db.sql("""
			select sum(debit-credit) as amount_sum
			from `tabJournal Entry Account`
			where reference_type='Payroll Entry'
				and reference_name=%s and docstatus=1
		""", self.name, as_list=True)

		journal_entries_amount_sum = flt(journal_entries_amount_sum[0][0]) if journal_entries_amount_sum else 0

		salary_slips = self.get_salary_slips_for_payment()
		ss_rounded_total_sum = sum([ss.rounded_total for ss in salary_slips])

		return 0 if journal_entries_amount_sum < ss_rounded_total_sum else 1

	def get_salary_slips_for_payment(self, include_draft=False):
		filter_cond = self.get_filter_condition()
		docstatus_cond = "ss.docstatus < 2" if include_draft else "ss.docstatus = 1"

		salary_slips = frappe.db.sql("""
			select ss.name, ss.employee, ss.employee_name,
				ss.salary_mode, ss.bank_name, ss.bank_account_no,
				ss.bank_amount, ss.cheque_amount, ss.cash_amount, ss.no_mode_amount,
				ss.net_pay, ss.rounded_total
			from `tabSalary Slip` ss
			where {0} and start_date >= %s and end_date <= %s {1}
		""".format(docstatus_cond, filter_cond), (self.start_date, self.end_date), as_dict=True)

		return salary_slips

	def get_disbursement_mode_details(self):
		salary_slips = self.get_salary_slips_for_payment()
		salary_modes = set([ss.salary_mode for ss in salary_slips if ss.salary_mode])
		bank_names = set([ss.bank_name for ss in salary_slips if ss.salary_mode == 'Bank' and ss.bank_name])

		return list(salary_modes), list(bank_names)

	def get_bank_details(self):
		sal_slips_in_payroll = self.get_salary_slips_for_payment(include_draft=True)
		sal_slips_in_payroll = [d for d in sal_slips_in_payroll if d.bank_amount and d.bank_name]

		bank_employee_map = {}
		for d in sal_slips_in_payroll:
			bank_name = d.bank_name
			bank_employee_map.setdefault(bank_name, frappe._dict({'employees': [], 'total': 0}))

			bank_employee_map[bank_name].employees.append({
				'employee': d.employee,
				'employee_name': d.employee_name,
				'bank_name': d.bank_name,
				'bank_account_no': d.bank_account_no,
				'rounded_total': d.rounded_total,
				'net_pay': d.net_pay,
				'bank_amount': d.bank_amount
			})
			bank_employee_map[bank_name].total += d.bank_amount

		return bank_employee_map

	def make_payment_entry(self, payment_account, salary_mode=None, bank_name=None, employee=None):
		from erpnext.accounts.utils import get_currency_precision

		self.check_permission('write')
		self.payment_account = payment_account

		salary_slips = self.get_salary_slips_for_payment()

		salary_mode_field = None
		if salary_mode:
			salary_mode_field = scrub(salary_mode) + '_amount'

		amount_field = salary_mode_field or 'rounded_total'

		if employee:
			salary_slips = [d for d in salary_slips if d.employee == employee]
		if salary_mode_field:
			salary_slips = [d for d in salary_slips if d.get(salary_mode_field)]
		if salary_mode == "Bank" and bank_name:
			salary_slips = [d for d in salary_slips if d.bank_name == bank_name]

		jv_names = []
		salary_slip_total = 0
		separate_jv_amount = 0
		if salary_slips:
			for ss in salary_slips:
				salary_slip = frappe.get_doc("Salary Slip", ss.name)
				salary_slip_total += flt(salary_slip.get(amount_field))
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
			.format(user_remark, formatdate(self.start_date), formatdate(self.end_date))
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

	def update_salary_slip_status(self, jv_name=None):
		ss_list = self.get_salary_slips(ss_status=1, as_dict=True)
		for ss in ss_list:
			frappe.db.set_value("Salary Slip", ss.name, "journal_entry", jv_name)

	def set_start_end_dates(self):
		self.update(get_start_end_dates(self.payroll_frequency, self.start_date or self.posting_date, self.company))

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
		holidays = 0

		holiday_list = get_holiday_list_for_employee(employee)
		if holiday_list:
			days = frappe.db.sql("""
				select count(*)
				from tabHoliday
				where parent=%s and holiday_date between %s and %s
			""", (holiday_list, self.start_date, self.end_date))

			if days and days[0][0]:
				holidays = days[0][0]

		return holidays

	def get_count_employee_attendance(self, employee):
		marked_days = 0

		attendances = frappe.db.sql("""
			select count(*)
			from tabAttendance
			where employee=%s and docstatus=1 and attendance_date between %s and %s
		""", (employee, self.start_date, self.end_date))

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
		select name
		from `tabPayroll Entry`
		where `{key}` LIKE %(txt)s
			and name not in (select reference_name from `tabJournal Entry Account` where reference_type='Payroll Entry')
		order by name limit %(start)s, %(page_len)s
	""".format(key=searchfield), {
		'txt': "%%%s%%" % frappe.db.escape(txt),
		'start': start,
		'page_len': page_len
	})
