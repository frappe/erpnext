# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext

from frappe.utils import add_days, cint, cstr, flt, getdate, rounded, date_diff, money_in_words
from frappe.model.naming import make_autoname

from frappe import msgprint, _
from erpnext.hr.doctype.payroll_entry.payroll_entry import get_start_end_dates
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.utilities.transaction_base import TransactionBase
from frappe.utils.background_jobs import enqueue

class SalarySlip(TransactionBase):
	def __init__(self, *args, **kwargs):
		super(SalarySlip, self).__init__(*args, **kwargs)
		self.series = 'Sal Slip/{0}/.#####'.format(self.employee)

	def autoname(self):
		self.name = make_autoname(self.series)

	def validate(self):
		self.status = self.get_status()
		self.validate_dates()
		self.check_existing()
		if not self.salary_slip_based_on_timesheet:
			self.get_date_details()

		if not (len(self.get("earnings")) or len(self.get("deductions"))):
			# get details from salary structure
			self.get_emp_and_leave_details()
		else:
			self.get_leave_details(lwp = self.leave_without_pay)

		# if self.salary_slip_based_on_timesheet or not self.net_pay:
		self.calculate_net_pay()

		company_currency = erpnext.get_company_currency(self.company)
		self.total_in_words = money_in_words(self.rounded_total, company_currency)

		if frappe.db.get_single_value("HR Settings", "max_working_hours_against_timesheet"):
			max_working_hours = frappe.db.get_single_value("HR Settings", "max_working_hours_against_timesheet")
			if self.salary_slip_based_on_timesheet and (self.total_working_hours > int(max_working_hours)):
				frappe.msgprint(_("Total working hours should not be greater than max working hours {0}").
								format(max_working_hours), alert=True)

	def validate_dates(self):
		if date_diff(self.end_date, self.start_date) < 0:
			frappe.throw(_("To date cannot be before From date"))

	def calculate_component_amounts(self):
		if not getattr(self, '_salary_structure_doc', None):
			self._salary_structure_doc = frappe.get_doc('Salary Structure', self.salary_structure)

		data = self.get_data_for_eval()

		for key in ('earnings', 'deductions'):
			for struct_row in self._salary_structure_doc.get(key):
				amount = self.eval_condition_and_formula(struct_row, data)
				if amount and struct_row.statistical_component == 0:
					self.update_component_row(struct_row, amount, key)

	def update_component_row(self, struct_row, amount, key):
		component_row = None
		for d in self.get(key):
			if d.salary_component == struct_row.salary_component:
				component_row = d

		if not component_row:
			self.append(key, {
				'amount': amount,
				'default_amount': amount,
				'depends_on_lwp' : struct_row.depends_on_lwp,
				'salary_component' : struct_row.salary_component,
				'abbr' : struct_row.abbr,
				'do_not_include_in_total' : struct_row.do_not_include_in_total
			})
		else:
			component_row.amount = amount

	def eval_condition_and_formula(self, d, data):
		try:
			condition = d.condition.strip() if d.condition else None
			if condition:
				if not frappe.safe_eval(condition, None, data):
					return None
			amount = d.amount
			if d.amount_based_on_formula:
				formula = d.formula.strip() if d.formula else None
				if formula:
					amount = frappe.safe_eval(formula, None, data)
			if amount:
				data[d.abbr] = amount

			return amount

		except NameError as err:
			frappe.throw(_("Name error: {0}".format(err)))
		except SyntaxError as err:
			frappe.throw(_("Syntax error in formula or condition: {0}".format(err)))
		except Exception as e:
			frappe.throw(_("Error in formula or condition: {0}".format(e)))
			raise

	def get_data_for_eval(self):
		'''Returns data for evaluating formula'''
		data = frappe._dict()

		data.update(frappe.get_doc("Salary Structure Employee",
			{"employee": self.employee, "parent": self.salary_structure}).as_dict())

		data.update(frappe.get_doc("Employee", self.employee).as_dict())
		data.update(self.as_dict())

		# set values for components
		salary_components = frappe.get_all("Salary Component", fields=["salary_component_abbr"])
		for sc in salary_components:
			data.setdefault(sc.salary_component_abbr, 0)

		for key in ('earnings', 'deductions'):
			for d in self.get(key):
				data[d.abbr] = d.amount

		return data


	def get_emp_and_leave_details(self):
		'''First time, load all the components from salary structure'''
		if self.employee:
			self.set("earnings", [])
			self.set("deductions", [])

			if not self.salary_slip_based_on_timesheet:
				self.get_date_details()
			self.validate_dates()
			joining_date, relieving_date = frappe.db.get_value("Employee", self.employee,
				["date_of_joining", "relieving_date"])

			self.get_leave_details(joining_date, relieving_date)
			struct = self.check_sal_struct(joining_date, relieving_date)

			if struct:
				self._salary_structure_doc = frappe.get_doc('Salary Structure', struct)
				self.salary_slip_based_on_timesheet = self._salary_structure_doc.salary_slip_based_on_timesheet or 0
				self.set_time_sheet()
				self.pull_sal_struct()

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

	def get_date_details(self):
		if not self.end_date:
			date_details = get_start_end_dates(self.payroll_frequency, self.start_date or self.posting_date)
			self.start_date = date_details.start_date
			self.end_date = date_details.end_date

	def check_sal_struct(self, joining_date, relieving_date):
		cond = ''
		if self.payroll_frequency:
			cond = """and payroll_frequency = '%(payroll_frequency)s'""" % {"payroll_frequency": self.payroll_frequency}

		st_name = frappe.db.sql("""select parent from `tabSalary Structure Employee`
			where employee=%s and (from_date <= %s or from_date <= %s)
			and (to_date is null or to_date >= %s or to_date >= %s)
			and parent in (select name from `tabSalary Structure`
				where is_active = 'Yes'%s)
			"""% ('%s', '%s', '%s','%s','%s', cond),(self.employee, self.start_date, joining_date, self.end_date, relieving_date))

		if st_name:
			if len(st_name) > 1:
				frappe.msgprint(_("Multiple active Salary Structures found for employee {0} for the given dates")
					.format(self.employee), title=_('Warning'))
			self.salary_structure = st_name and st_name[0][0] or ''
			return self.salary_structure
		else:
			self.salary_structure = None
			frappe.msgprint(_("No active or default Salary Structure found for employee {0} for the given dates")
				.format(self.employee), title=_('Salary Structure Missing'))

	def pull_sal_struct(self):
		from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip

		if self.salary_slip_based_on_timesheet:
			self.salary_structure = self._salary_structure_doc.name
			self.hour_rate = self._salary_structure_doc.hour_rate
			self.total_working_hours = sum([d.working_hours or 0.0 for d in self.timesheets]) or 0.0
			wages_amount = self.hour_rate * self.total_working_hours

			self.add_earning_for_hourly_wages(self, self._salary_structure_doc.salary_component, wages_amount)

		make_salary_slip(self._salary_structure_doc.name, self)

	def process_salary_structure(self):
		'''Calculate salary after salary structure details have been updated'''
		if not self.salary_slip_based_on_timesheet:
			self.get_date_details()
		self.pull_emp_details()
		self.get_leave_details()
		self.calculate_net_pay()

	def add_earning_for_hourly_wages(self, doc, salary_component, amount):
		row_exists = False
		for row in doc.earnings:
			if row.salary_component == salary_component:
				row.amount = amount
				row_exists = True
				break

		if not row_exists:
			wages_row = {
				"salary_component": salary_component,
				"abbr": frappe.db.get_value("Salary Component", salary_component, "salary_component_abbr"),
				"amount": self.hour_rate * self.total_working_hours
			}
			doc.append('earnings', wages_row)

	def pull_emp_details(self):
		emp = frappe.db.get_value("Employee", self.employee, ["bank_name", "bank_ac_no"], as_dict=1)
		if emp:
			self.bank_name = emp.bank_name
			self.bank_account_no = emp.bank_ac_no


	def get_leave_details(self, joining_date=None, relieving_date=None, lwp=None):
		if not joining_date:
			joining_date, relieving_date = frappe.db.get_value("Employee", self.employee,
				["date_of_joining", "relieving_date"])

		holidays = self.get_holidays_for_employee(self.start_date, self.end_date)
		working_days = date_diff(self.end_date, self.start_date) + 1
		actual_lwp = self.calculate_lwp(holidays, working_days)
		if not cint(frappe.db.get_value("HR Settings", None, "include_holidays_in_total_working_days")):
			working_days -= len(holidays)
			if working_days < 0:
				frappe.throw(_("There are more holidays than working days this month."))

		if not lwp:
			lwp = actual_lwp
		elif lwp != actual_lwp:
			frappe.msgprint(_("Leave Without Pay does not match with approved Leave Application records"))

		self.total_working_days = working_days
		self.leave_without_pay = lwp

		payment_days = flt(self.get_payment_days(joining_date, relieving_date)) - flt(lwp)
		self.payment_days = payment_days > 0 and payment_days or 0

	def get_payment_days(self, joining_date, relieving_date):
		start_date = getdate(self.start_date)
		if joining_date:
			if getdate(self.start_date) <= joining_date <= getdate(self.end_date):
				start_date = joining_date
			elif joining_date > getdate(self.end_date):
				return

		end_date = getdate(self.end_date)
		if relieving_date:
			if getdate(self.start_date) <= relieving_date <= getdate(self.end_date):
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
		holidays = "','".join(holidays)
		for d in range(working_days):
			dt = add_days(cstr(getdate(self.start_date)), d)
			leave = frappe.db.sql("""
				select t1.name, t1.half_day
				from `tabLeave Application` t1, `tabLeave Type` t2
				where t2.name = t1.leave_type
				and t2.is_lwp = 1
				and t1.docstatus = 1
				and t1.status = 'Approved'
				and t1.employee = %(employee)s
				and CASE WHEN t2.include_holiday != 1 THEN %(dt)s not in ('{0}') and %(dt)s between from_date and to_date
				WHEN t2.include_holiday THEN %(dt)s between from_date and to_date
				END
				""".format(holidays), {"employee": self.employee, "dt": dt})
			if leave:
				lwp = cint(leave[0][1]) and (lwp + 0.5) or (lwp + 1)
		return lwp

	def check_existing(self):
		if not self.salary_slip_based_on_timesheet:
			ret_exist = frappe.db.sql("""select name from `tabSalary Slip`
						where start_date = %s and end_date = %s and docstatus != 2
						and employee = %s and name != %s""",
						(self.start_date, self.end_date, self.employee, self.name))
			if ret_exist:
				self.employee = ''
				frappe.throw(_("Salary Slip of employee {0} already created for this period").format(self.employee))
		else:
			for data in self.timesheets:
				if frappe.db.get_value('Timesheet', data.time_sheet, 'status') == 'Payrolled':
					frappe.throw(_("Salary Slip of employee {0} already created for time sheet {1}").format(self.employee, data.time_sheet))

	def sum_components(self, component_type, total_field):
		joining_date, relieving_date = frappe.db.get_value("Employee", self.employee,
			["date_of_joining", "relieving_date"])
		
		if not relieving_date:
			relieving_date = getdate(self.end_date)

		if not joining_date:
			frappe.throw(_("Please set the Date Of Joining for employee {0}").format(frappe.bold(self.employee_name)))

		for d in self.get(component_type):
			if (self.salary_structure and
				cint(d.depends_on_lwp) and
				(not
				    self.salary_slip_based_on_timesheet or
					getdate(self.start_date) < joining_date or
					getdate(self.end_date) > relieving_date
				)):

				d.amount = rounded(
					(flt(d.default_amount) * flt(self.payment_days)
					/ cint(self.total_working_days)), self.precision("amount", component_type)
				)

			elif not self.payment_days and not self.salary_slip_based_on_timesheet and \
				cint(d.depends_on_lwp):
				d.amount = 0
			elif not d.amount:
				d.amount = d.default_amount
			if not d.do_not_include_in_total:
				self.set(total_field, self.get(total_field) + flt(d.amount, 2))

	def calculate_net_pay(self):
		if self.salary_structure:
			self.calculate_component_amounts()

		disable_rounded_total = cint(frappe.db.get_value("Global Defaults", None, "disable_rounded_total"))

		self.total_deduction = 0
		self.gross_pay = 0

		self.sum_components('earnings', 'gross_pay')
		self.sum_components('deductions', 'total_deduction')

		self.set_loan_repayment()

		self.net_pay = flt(self.gross_pay) - (flt(self.total_deduction) + flt(self.total_loan_repayment))
		self.rounded_total = rounded(self.net_pay,
			self.precision("net_pay") if disable_rounded_total else 0)

	def set_loan_repayment(self):
		self.set('loans', [])
		self.total_loan_repayment = 0
		self.total_interest_amount = 0
		self.total_principal_amount = 0

		for loan in self.get_employee_loan_details():
			self.append('loans', {
				'employee_loan': loan.name,
				'total_payment': loan.total_payment,
				'interest_amount': loan.interest_amount,
				'principal_amount': loan.principal_amount,
				'employee_loan_account': loan.employee_loan_account,
				'interest_income_account': loan.interest_income_account
			})

			self.total_loan_repayment += loan.total_payment
			self.total_interest_amount += loan.interest_amount
			self.total_principal_amount += loan.principal_amount

	def get_employee_loan_details(self):
		return frappe.db.sql("""select rps.principal_amount, rps.interest_amount, el.name,
				rps.total_payment, el.employee_loan_account, el.interest_income_account
			from
				`tabRepayment Schedule` as rps, `tabEmployee Loan` as el
			where
				el.name = rps.parent and rps.payment_date between %s and %s and
				el.repay_from_salary = 1 and el.docstatus = 1 and el.employee = %s""",
			(self.start_date, self.end_date, self.employee), as_dict=True) or []

	def on_submit(self):
		if self.net_pay < 0:
			frappe.throw(_("Net Pay cannot be less than 0"))
		else:
			self.set_status()
			self.update_status(self.name)
			if(frappe.db.get_single_value("HR Settings", "email_salary_slip_to_employee")) and not frappe.flags.via_payroll_entry:
				self.email_salary_slip()

	def on_cancel(self):
		self.set_status()
		self.update_status()

	def on_trash(self):
		from frappe.model.naming import revert_series_if_last
		revert_series_if_last(self.series, self.name)

	def email_salary_slip(self):
		receiver = frappe.db.get_value("Employee", self.employee, "prefered_email")

		if receiver:
			email_args = {
				"recipients": [receiver],
				"message": _("Please see attachment"),
				"subject": 'Salary Slip - from {0} to {1}'.format(self.start_date, self.end_date),
				"attachments": [frappe.attach_print(self.doctype, self.name, file_name=self.name)],
				"reference_doctype": self.doctype,
				"reference_name": self.name
				}
			enqueue(method=frappe.sendmail, queue='short', timeout=300, async=True, **email_args)
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

	def set_status(self, status=None):
		'''Get and update status'''
		if not status:
			status = self.get_status()
		self.db_set("status", status)

	def get_status(self):
		if self.docstatus == 0:
			status = "Draft"
		elif self.docstatus == 1:
			status = "Submitted"
		elif self.docstatus == 2:
			status = "Cancelled"
		return status

def unlink_ref_doc_from_salary_slip(ref_no):
	linked_ss = frappe.db.sql_list("""select name from `tabSalary Slip`
	where journal_entry=%s and docstatus < 2""", (ref_no))
	if linked_ss:
		for ss in linked_ss:
			ss_doc = frappe.get_doc("Salary Slip", ss)
			frappe.db.set_value("Salary Slip", ss_doc.name, "journal_entry", "")
