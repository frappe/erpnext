# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate, rounded, date_diff
from frappe.model.naming import make_autoname

from frappe import msgprint, _
from erpnext.setup.utils import get_company_currency
from erpnext.hr.utils import set_employee_name
from erpnext.hr.doctype.process_payroll.process_payroll import get_month_details

from erpnext.utilities.transaction_base import TransactionBase

class SalarySlip(TransactionBase):
	def autoname(self):
		self.name = make_autoname('Sal Slip/' +self.employee + '/.#####')

	def get_emp_and_leave_details(self):
		if self.employee:
			joining_date, relieving_date = frappe.db.get_value("Employee", self.employee, 
				["date_of_joining", "relieving_date"])
				
			self.get_leave_details(joining_date, relieving_date)
			
			struct = self.check_sal_struct(joining_date, relieving_date)
			if struct:
				self.set("earnings", [])
				self.set("deduction", [])
				self.pull_sal_struct(struct)

	def check_sal_struct(self, joining_date, relieving_date):
		m = get_month_details(self.fiscal_year, self.month)
		
		struct = frappe.db.sql("""select name from `tabSalary Structure`
			where employee=%s and is_active = 'Yes'
			and (from_date <= %s or from_date <= %s) 
			and (to_date is null or to_date >= %s or to_date >= %s)""",
			(self.employee, m.month_start_date, joining_date, m.month_end_date, relieving_date))

		if not struct:
			msgprint(_("No active Salary Structure found for employee {0} and the month")
				.format(self.employee))
			self.employee = None

		return struct and struct[0][0] or ''

	def pull_sal_struct(self, struct):
		from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
		make_salary_slip(struct, self)

	def pull_emp_details(self):
		emp = frappe.db.get_value("Employee", self.employee, ["bank_name", "bank_ac_no"], as_dict=1)
		if emp:
			self.bank_name = emp.bank_name
			self.bank_account_no = emp.bank_ac_no

	def get_leave_details(self, joining_date=None, relieving_date=None, lwp=None):
		if not self.fiscal_year:
			self.fiscal_year = frappe.db.get_default("fiscal_year")
		if not self.month:
			self.month = "%02d" % getdate(nowdate()).month
			
		if not joining_date:
			joining_date, relieving_date = frappe.db.get_value("Employee", self.employee, 
				["date_of_joining", "relieving_date"])

		m = get_month_details(self.fiscal_year, self.month)
		holidays = self.get_holidays_for_employee(m['month_start_date'], m['month_end_date'])

		working_days = m["month_days"]
		if not cint(frappe.db.get_value("HR Settings", None, "include_holidays_in_total_working_days")):
			working_days -= len(holidays)
			if working_days < 0:
				frappe.throw(_("There are more holidays than working days this month."))

		if not lwp:
			lwp = self.calculate_lwp(holidays, m)
		self.total_days_in_month = working_days
		self.leave_without_pay = lwp
		payment_days = flt(self.get_payment_days(m, joining_date, relieving_date)) - flt(lwp)
		self.payment_days = payment_days > 0 and payment_days or 0
		
	def get_payment_days(self, month, joining_date, relieving_date):
		start_date = month['month_start_date']
		if joining_date:
			if joining_date > month['month_start_date']:
				start_date = joining_date
			elif joining_date > month['month_end_date']:
				return
				
		end_date = month['month_end_date']
		if relieving_date:
			if relieving_date > start_date and relieving_date < month['month_end_date']:
				end_date = relieving_date
			elif relieving_date < month['month_start_date']:
				frappe.throw(_("Employee relieved on {0} must be set as 'Left'")
					.format(relieving_date))			
			
		payment_days = date_diff(end_date, start_date) + 1

		if not cint(frappe.db.get_value("HR Settings", None, "include_holidays_in_total_working_days")):
			holidays = self.get_holidays_for_employee(start_date, end_date)
			payment_days -= len(holidays)

		return payment_days

	def get_holidays_for_employee(self, start_date, end_date):
		holidays = frappe.db.sql("""select t1.holiday_date
			from `tabHoliday` t1, tabEmployee t2
			where t1.parent = t2.holiday_list and t2.name = %s
			and t1.holiday_date between %s and %s""",
			(self.employee, start_date, end_date))
			
		if not holidays:
			holidays = frappe.db.sql("""select t1.holiday_date
				from `tabHoliday` t1, `tabHoliday List` t2
				where t1.parent = t2.name and t2.is_default = 1
				and t2.fiscal_year = %s
				and t1.holiday_date between %s and %s""", 
				(self.fiscal_year, start_date, end_date))
		
		holidays = [cstr(i[0]) for i in holidays]
		return holidays

	def calculate_lwp(self, holidays, m):
		lwp = 0
		for d in range(m['month_days']):
			dt = add_days(cstr(m['month_start_date']), d)
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
		ret_exist = frappe.db.sql("""select name from `tabSalary Slip`
			where month = %s and fiscal_year = %s and docstatus != 2
			and employee = %s and name != %s""",
			(self.month, self.fiscal_year, self.employee, self.name))
		if ret_exist:
			self.employee = ''
			frappe.throw(_("Salary Slip of employee {0} already created for this month").format(self.employee))

	def validate(self):
		from frappe.utils import money_in_words
		self.check_existing()

		if not (len(self.get("earnings")) or len(self.get("deductions"))):
			self.get_emp_and_leave_details()
		else:
			self.get_leave_details(lwp = self.leave_without_pay)

		if not self.net_pay:
			self.calculate_net_pay()

		company_currency = get_company_currency(self.company)
		self.total_in_words = money_in_words(self.rounded_total, company_currency)

		set_employee_name(self)

	def calculate_earning_total(self):
		self.gross_pay = flt(self.arrear_amount) + flt(self.leave_encashment_amount)
		for d in self.get("earnings"):
			if cint(d.e_depends_on_lwp) == 1:
				d.e_modified_amount = rounded((flt(d.e_amount) * flt(self.payment_days)
					/ cint(self.total_days_in_month)), self.precision("e_modified_amount", "earnings"))
			elif not self.payment_days:
				d.e_modified_amount = 0
			elif not d.e_modified_amount:
				d.e_modified_amount = d.e_amount
			self.gross_pay += flt(d.e_modified_amount)

	def calculate_ded_total(self):
		self.total_deduction = 0
		for d in self.get('deductions'):
			if cint(d.d_depends_on_lwp) == 1:
				d.d_modified_amount = rounded((flt(d.d_amount) * flt(self.payment_days)
					/ cint(self.total_days_in_month)), self.precision("d_modified_amount", "deductions"))
			elif not self.payment_days:
				d.d_modified_amount = 0
			elif not d.d_modified_amount:
				d.d_modified_amount = d.d_amount

			self.total_deduction += flt(d.d_modified_amount)

	def calculate_net_pay(self):
		disable_rounded_total = cint(frappe.db.get_value("Global Defaults", None, "disable_rounded_total"))

		self.calculate_earning_total()
		self.calculate_ded_total()
		self.net_pay = flt(self.gross_pay) - flt(self.total_deduction)
		self.rounded_total = rounded(self.net_pay,
			self.precision("net_pay") if disable_rounded_total else 0)

	def on_submit(self):
		if(self.email_check == 1):
			self.send_mail_funct()


	def send_mail_funct(self):
		receiver = frappe.db.get_value("Employee", self.employee, "company_email")
		if receiver:
			subj = 'Salary Slip - ' + cstr(self.month) +'/'+cstr(self.fiscal_year)
			frappe.sendmail([receiver], subject=subj, message = _("Please see attachment"),
				attachments=[frappe.attach_print(self.doctype, self.name, file_name=self.name)])
		else:
			msgprint(_("Company Email ID not found, hence mail not sent"))
