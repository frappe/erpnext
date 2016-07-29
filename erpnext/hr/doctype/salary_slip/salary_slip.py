# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate, rounded, date_diff, money_in_words
from frappe.model.naming import make_autoname

from frappe import msgprint, _
from erpnext.accounts.utils import get_fiscal_year
from erpnext.setup.utils import get_company_currency
from erpnext.hr.utils import set_employee_name
from erpnext.hr.doctype.process_payroll.process_payroll import get_month_details
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.utilities.transaction_base import TransactionBase

class SalarySlip(TransactionBase):
	def autoname(self):
		self.name = make_autoname('Sal Slip/' +self.employee + '/.#####')

	def validate(self):
		self.validate_dates()
		self.check_existing()
		self.set_month_dates()
		
		if not (len(self.get("earnings")) or len(self.get("deductions"))):
			self.get_emp_and_leave_details()
		else:
			self.get_leave_details(lwp = self.leave_without_pay)

		if self.salary_slip_based_on_timesheet or not self.net_pay:
			self.calculate_net_pay()

		company_currency = get_company_currency(self.company)
		self.total_in_words = money_in_words(self.rounded_total, company_currency)

		set_employee_name(self)

	def validate_dates(self):
		if date_diff(self.end_date, self.start_date) < 0:
			frappe.throw(_("To date cannot be before From date"))

	def get_emp_and_leave_details(self):
		if self.employee:
			self.set("earnings", [])
			self.set("deductions", [])

			self.set_month_dates()
			self.validate_dates()
			joining_date, relieving_date = frappe.db.get_value("Employee", self.employee,
				["date_of_joining", "relieving_date"])

			self.get_leave_details(joining_date, relieving_date)
			struct = self.check_sal_struct(joining_date, relieving_date)

			if struct:
				ss_doc = frappe.get_doc('Salary Structure', struct)
				self.salary_slip_based_on_timesheet = ss_doc.salary_slip_based_on_timesheet or 0
				self.set_time_sheet()
				self.pull_sal_struct(ss_doc)

	def set_time_sheet(self):
		if self.salary_slip_based_on_timesheet:
			self.set("timesheets", [])
			timesheets = frappe.db.sql(""" select * from `tabTimesheet` where employee = %(employee)s and start_date BETWEEN %(start_date)s AND %(end_date)s and (status = 'Submitted' or
				status = 'Billed')""", {'employee': self.employee, 'start_date': self.start_date, 'end_date': self.end_date}, as_dict=1)

			for data in timesheets:
				self.append('timesheets', {
					'time_sheet': data.name,
					'working_hours': data.total_hours
				})

	def set_month_dates(self):
		if self.month and not self.salary_slip_based_on_timesheet:
			m = get_month_details(self.fiscal_year, self.month)
			self.start_date = m['month_start_date']
			self.end_date = m['month_end_date']

	def check_sal_struct(self, joining_date, relieving_date):
		struct = frappe.db.sql("""select name from `tabSalary Structure`
			where employee=%s and is_active = 'Yes'
			and (from_date <= %s or from_date <= %s)
			and (to_date is null or to_date >= %s or to_date >= %s) order by from_date desc limit 1""",
			(self.employee, self.start_date, joining_date, self.end_date, relieving_date))

		if not struct:
			self.salary_structure = None
			frappe.throw(_("No active or default Salary Structure found for employee {0} for the given dates")
				.format(self.employee), title=_('Salary Structure Missing'))

		return struct and struct[0][0] or ''

	def pull_sal_struct(self, ss_doc):
		from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
		make_salary_slip(ss_doc.name, self)

		if self.salary_slip_based_on_timesheet:
			self.salary_structure = ss_doc.name
			self.hour_rate = ss_doc.hour_rate
			self.total_working_hours = sum([d.working_hours or 0.0 for d in self.timesheets]) or 0.0
			self.add_earning_for_hourly_wages(ss_doc.salary_component)

	def add_earning_for_hourly_wages(self, salary_component):
		default_type = False
		for data in self.earnings:
			if data.salary_component == salary_component:
				data.amount = self.hour_rate * self.total_working_hours
				default_type = True
				break

		if not default_type:
			earnings = self.append('earnings', {})
			earnings.salary_component = salary_component
			earnings.amount = self.hour_rate * self.total_working_hours

	def pull_emp_details(self):
		emp = frappe.db.get_value("Employee", self.employee, ["bank_name", "bank_ac_no"], as_dict=1)
		if emp:
			self.bank_name = emp.bank_name
			self.bank_account_no = emp.bank_ac_no

	def get_leave_details(self, joining_date=None, relieving_date=None, lwp=None):
		if not self.fiscal_year:
			# if default fiscal year is not set, get from nowdate
			self.fiscal_year = get_fiscal_year(nowdate())[0]

		if not self.month:
			self.month = "%02d" % getdate(nowdate()).month
			self.set_month_dates()

		if not joining_date:
			joining_date, relieving_date = frappe.db.get_value("Employee", self.employee,
				["date_of_joining", "relieving_date"])

		holidays = self.get_holidays_for_employee(self.start_date, self.end_date)

		working_days = date_diff(self.end_date, self.start_date) + 1
		if not cint(frappe.db.get_value("HR Settings", None, "include_holidays_in_total_working_days")):
			working_days -= len(holidays)
			if working_days < 0:
				frappe.throw(_("There are more holidays than working days this month."))

		if not lwp:
			lwp = self.calculate_lwp(holidays, working_days)
		self.total_days_in_month = working_days
		self.leave_without_pay = lwp
		payment_days = flt(self.get_payment_days(joining_date, relieving_date)) - flt(lwp)
		self.payment_days = payment_days > 0 and payment_days or 0

	def get_payment_days(self, joining_date, relieving_date):
		start_date = getdate(self.start_date)

		if joining_date:
			if joining_date > getdate(self.start_date):
				start_date = joining_date
			elif joining_date > getdate(self.end_date):
				return

		end_date = getdate(self.end_date)
		if relieving_date:
			if relieving_date > start_date and relieving_date < getdate(self.end_date):
				end_date = relieving_date
			elif relieving_date < getdate(self.start_date):
				frappe.throw(_("Employee relieved on {0} must be set as 'Left'")
					.format(relieving_date))

		payment_days = date_diff(end_date, start_date) + 1

		if not cint(frappe.db.get_value("HR Settings", None, "include_holidays_in_total_working_days")):
			holidays = self.get_holidays_for_employee(start_date, end_date)
			payment_days -= len(holidays)

		return payment_days

	def get_holidays_for_employee(self, start_date, end_date):
		holiday_list = get_holiday_list_for_employee(self.employee)
		holidays = frappe.db.sql_list('''select holiday_date from `tabHoliday`
			where
				parent=%(holiday_list)s
				and holiday_date >= %(start_date)s
				and holiday_date <= %(end_date)s''', {
					"holiday_list": holiday_list,
					"start_date": start_date,
					"end_date": end_date
				})

		holidays = [cstr(i) for i in holidays]

		return holidays

	def calculate_lwp(self, holidays, working_days):
		lwp = 0
		for d in range(working_days):
			dt = add_days(cstr(self.start_date), d)
			if dt not in holidays:
				leave = frappe.db.sql("""
					select t1.name, t1.half_day
					from `tabLeave Application` t1, `tabLeave Type` t2
					where t2.name = t1.leave_type
					and t2.is_lwp = 1
					and t1.docstatus = 1
					and t1.employee = %s
					and %s between from_date and to_date
				""", (self.employee, dt))
				if leave:
					lwp = cint(leave[0][1]) and (lwp + 0.5) or (lwp + 1)
		return lwp

	def check_existing(self):
		if not self.salary_slip_based_on_timesheet:
			ret_exist = frappe.db.sql("""select name from `tabSalary Slip`
						where month = %s and fiscal_year = %s and docstatus != 2
						and employee = %s and name != %s""",
						(self.month, self.fiscal_year, self.employee, self.name))
			if ret_exist:
				self.employee = ''
				frappe.throw(_("Salary Slip of employee {0} already created for this period").format(self.employee))
		else:
			for data in self.timesheets:
				if frappe.db.get_value('Timesheet', data.time_sheet, 'status') == 'Payrolled':
					frappe.throw(_("Salary Slip of employee {0} already created for time sheet {1}").format(self.employee, data.time_sheet))

	def calculate_earning_total(self):
		self.gross_pay = flt(self.arrear_amount) + flt(self.leave_encashment_amount)
		for d in self.get("earnings"):
			if cint(d.depends_on_lwp) == 1 and not self.salary_slip_based_on_timesheet:
				d.amount = rounded((flt(d.default_amount) * flt(self.payment_days)
					/ cint(self.total_days_in_month)), self.precision("amount", "earnings"))
			elif not self.payment_days and not self.salary_slip_based_on_timesheet:
				d.amount = 0
			elif not d.amount:
				d.amount = d.default_amount
			self.gross_pay += flt(d.amount)

	def calculate_ded_total(self):
		self.total_deduction = 0
		for d in self.get('deductions'):
			if cint(d.depends_on_lwp) == 1 and not self.salary_slip_based_on_timesheet:
				d.amount = rounded((flt(d.amount) * flt(self.payment_days)
					/ cint(self.total_days_in_month)), self.precision("amount", "deductions"))
			elif not self.payment_days and not self.salary_slip_based_on_timesheet:
				d.amount = 0
			elif not d.amount:
				d.amount = d.default_amount
			self.total_deduction += flt(d.amount)

	def calculate_net_pay(self):
		disable_rounded_total = cint(frappe.db.get_value("Global Defaults", None, "disable_rounded_total"))

		self.calculate_earning_total()
		self.calculate_ded_total()
		self.net_pay = flt(self.gross_pay) - flt(self.total_deduction)
		self.rounded_total = rounded(self.net_pay,
			self.precision("net_pay") if disable_rounded_total else 0)

	def on_submit(self):
		self.update_status(self.name)
		if(frappe.db.get_single_value("HR Settings", "email_salary_slip_to_employee")):
			self.email_salary_slip()

	def on_cancel(self):
		self.update_status()

	def email_salary_slip(self):
		receiver = frappe.db.get_value("Employee", self.employee, "company_email") or \
			frappe.db.get_value("Employee", self.employee, "personal_email")
		if receiver:
			subj = 'Salary Slip - from {0} to {1}, fiscal year {2}'.format(self.start_date, self.end_date, self.fiscal_year)
			frappe.sendmail([receiver], subject=subj, message = _("Please see attachment"),
				attachments=[frappe.attach_print(self.doctype, self.name, file_name=self.name)], reference_doctype= self.doctype, reference_name= self.name)
		else:
			msgprint(_("{0}: Employee email not found, hence email not sent").format(self.employee_name))

	def update_status(self, salary_slip=None):
		for data in self.timesheets:
			if data.time_sheet:
				timesheet = frappe.get_doc('Timesheet', data.time_sheet)
				timesheet.salary_slip = salary_slip
				timesheet.flags.ignore_validate_update_after_submit = True
				timesheet.set_status()
				timesheet.save()