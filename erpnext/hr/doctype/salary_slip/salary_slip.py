# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import add_days, cint, cstr, flt, getdate, rounded, date_diff, money_in_words, get_first_day, get_last_day
from frappe.model.naming import make_autoname

from frappe import msgprint, _
from erpnext.setup.utils import get_company_currency
from erpnext.hr.doctype.process_payroll.process_payroll import get_start_end_dates
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.utilities.transaction_base import TransactionBase

class SalarySlip(TransactionBase):
	def autoname(self):
		self.name = make_autoname('Sal Slip/' +self.employee + '/.#####')

	def validate(self):
		self.validate_overtime()
		# self.validate_return_from_leave_deduction()
		self.status = self.get_status()

		pan=frappe.get_value("Penalty",filters={'start_date':self.start_date,'end_date':self.end_date,'employee':self.employee, 'docstatus': 1}, fieldname="name")
		if pan:
			pen_doc=frappe.get_doc("Penalty",pan)	
			pen_doc.flags.ignore_permissions = True
			if pen_doc:
				if pen_doc.penalty_type=="Amount":
					self.penalty_amount=pen_doc.amount
				elif pen_doc.penalty_type=="Days":
					self.penalty_days=pen_doc.days_count

		self.validate_dates()
		self.check_existing()
		self.get_date_details()
		if not (len(self.get("earnings")) or len(self.get("deductions"))):
			# get details from salary structure
			self.get_emp_and_leave_details()
		else:
			self.get_leave_details(lwp = self.leave_without_pay)

		# if self.salary_slip_based_on_timesheet or not self.net_pay:
		self.calculate_net_pay()

		company_currency = get_company_currency(self.company)
		self.total_in_words = money_in_words(self.rounded_total, company_currency)

		if frappe.db.get_single_value("HR Settings", "max_working_hours_against_timesheet"):
			max_working_hours = frappe.db.get_single_value("HR Settings", "max_working_hours_against_timesheet")
			if self.salary_slip_based_on_timesheet and (self.total_working_hours > int(max_working_hours)):
				frappe.msgprint(_("Total working hours should not be greater than max working hours {0}").
								format(max_working_hours), alert=True)
		self.validate_return_from_leave_deduction()
		self.get_join_date_deducted_days()

	def validate_overtime(self):
		prev_month = getdate(self.start_date).month - 1 if getdate(self.start_date).month - 1 > 0 else 12
		prev_month_start_date = None
		prev_month_end_date = None
		if prev_month != 12:
			prev_month_start_date = "{0}-{1}-01".format(getdate(self.start_date).year, prev_month)
			prev_month_start_date_object = getdate(prev_month_start_date)
			prev_month_end_date = get_last_day(prev_month_start_date_object)
		else:
			prev_month_start_date = "{0}-{1}-01".format(getdate(self.start_date).year - 1, prev_month)
			prev_month_start_date_object = getdate(prev_month_start_date)
			prev_month_end_date = get_last_day(prev_month_start_date_object)

		overtime_hours = frappe.db.sql("""Select total_modified_hours from `tabOvertime Request` where
		 from_date between '{0}' and '{1}' and employee = '{2}' and docstatus = 1
		 order by modified desc limit 1""".format(prev_month_start_date,prev_month_end_date, self.employee), as_dict=True)
		if overtime_hours:
			self.overtime_hours = overtime_hours[0].total_modified_hours

	def validate_return_from_leave_deduction(self):
		# if self.docstatus == 0:
		# end_date = "{0}-{1}-20".format(getdate(self.end_date).year, getdate(self.end_date).month)
		# prev_month = getdate(self.end_date).month - 1 if getdate(self.end_date).month - 1 > 0 else 12
		# prev_month_start_date = ""
		# if prev_month != 12:
		# 	prev_month_start_date = "{0}-{1}-20".format(getdate(self.end_date).year, prev_month)
		# else:
		# 	prev_month_start_date = "{0}-{1}-20".format(getdate(self.end_date).year - 1, prev_month)
		# self.set_deduction_for_return_from_leave(prev_month_start_date, end_date)
		if self.get('__islocal'):
			self.set_deduction_for_return_from_leave(self.start_date, self.end_date)

	def get_join_date_deducted_days(self):
		if getdate(self.date_of_joining).month == getdate(self.start_date).month and getdate(self.date_of_joining).year == getdate(self.start_date).year:
			date_dif = date_diff(self.date_of_joining, get_first_day(getdate(self.date_of_joining)))
			if date_dif > 0:
				self.jd_deducted_days = date_dif	
				ss = frappe.get_doc("Salary Structure", self.salary_structure)
				for doc in ss.get("earnings"):
					if doc.get("salary_component") == "Basic":
						doc.set("formula", "base-((base/30)*(jd_deducted_days))")

				ss.save(ignore_permissions=True)
	# def get_emp_join_date(self,employee):
	# 	"""  Get Employee Joinin Date"""
	# 	date_of_joining=frappe.get_value('Employee',self.employee,'date_of_joining');
	# 	return date_of_joining


	# def check_date(self,date_of_joining):
	# 	""" return number of days differnt  """

	# 	"""  check if the year, month is the same current salry slip month,year
	# 	check the day if they are 1 start or not """

	# 	start_date =self.start_date
	# 	star_day = getdate(self.start_date).day
	# 	star_month=getdate(self.start_date).month
	# 	start_year=getdate(self.start_date).year

	# 	join_day = getdate(date_of_joining).day
	# 	join_month=getdate(date_of_joining).month
	# 	join_year=getdate(date_of_joining).year



	# 	if start_year ==  join_year and star_month == join_month :
	# 		if start_day==join_day:
	# 			pass
	# 		elif star_day > join_day:
	# 			pass
	# 		elif star_day <join:
	# 			""" get the differance """
	# 			pass

	def set_deduction_for_return_from_leave(self, start_date, end_date):

		rt = frappe.db.sql(""" select to_date, return_date from `tabReturn From Leave Statement` where docstatus = 1 and
		employee = '{0}' and return_date between '{1}' and '{2}'""".format(self.employee, start_date, end_date), as_dict = True)

		if rt:
			deducted_days = 0
			for r in rt:
				holidays = self.get_holidays_for_employee(r.to_date, r.return_date)
				deducted_days += date_diff(r.return_date, r.to_date)
				deducted_days -= len(holidays)
				if deducted_days > 1:
					deducted_days = deducted_days - 1
			self.deducted_days = deducted_days

	def validate_dates(self):
		if date_diff(self.end_date, self.start_date) < 0:
			frappe.throw(_("To date cannot be before From date"))

	def calculate_component_amounts(self):
		import math

		if not getattr(self, '_salary_structure_doc', None):
			self._salary_structure_doc = frappe.get_doc('Salary Structure', self.salary_structure)

		data = self.get_data_for_eval()
		for key in ('earnings', 'deductions'):
			for struct_row in self._salary_structure_doc.get(key):
				amount = self.eval_condition_and_formula(struct_row, data)
				if amount:
					#~ amount = math.ceil(amount)'
					# if struct_row.salary_component == "GOSY":
					# 	pass
						# amount = math.ceil(amount)
				

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
				'salary_component' : struct_row.salary_component
			})
		else:
			component_row.amount = amount

	def eval_condition_and_formula(self, d, data):
		try:
			if d.condition:
				if not eval(d.condition, None, data):
					return None
			amount = d.amount
			if d.amount_based_on_formula:
				if d.formula:
					amount = eval(d.formula, None, data)
			if amount:
				data[d.abbr] = amount
			return amount

		except NameError as err:
		    frappe.throw(_("Name error: {0}".format(err)))
		except SyntaxError as err:
		    frappe.throw(_("Syntax error in formula or condition: {0}".format(err)))
		except:
		    frappe.throw(_("Error in formula or condition"))
		    raise

	def get_data_for_eval(self):
		'''Returns data for evaluating formula'''
		data = frappe._dict()

		for d in self._salary_structure_doc.employees:
			if d.employee == self.employee:
				data.base, data.variable = d.base, d.variable

		data.update(frappe.get_doc("Employee", self.employee).as_dict())
		data.update(self.as_dict())

		# set values for components
		salary_components = frappe.get_all("Salary Component", fields=["salary_component_abbr"])
		for salary_component in salary_components:
			data[salary_component.salary_component_abbr] = 0

		return data


	def get_emp_and_leave_details(self):
		'''First time, load all the components from salary structure'''
		if self.employee:
			self.set("earnings", [])
			self.set("deductions", [])

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
			return st_name and st_name[0][0] or ''
		else:
			self.salary_structure = None
			frappe.msgprint(_("No active or default Salary Structure found for employee {0} for the given dates")
				.format(self.employee), title=_('Salary Structure Missing'))

	def pull_sal_struct(self):
		from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
		make_salary_slip(self._salary_structure_doc.name, self)

		if self.salary_slip_based_on_timesheet:
			self.salary_structure = self._salary_structure_doc.name
			self.hour_rate = self._salary_structure_doc.hour_rate
			self.total_working_hours = sum([d.working_hours or 0.0 for d in self.timesheets]) or 0.0
			self.add_earning_for_hourly_wages(self._salary_structure_doc.salary_component)

	def process_salary_structure(self):
		'''Calculate salary after salary structure details have been updated'''
		self.get_date_details()
		self.pull_emp_details()
		self.get_leave_details()
		self.calculate_net_pay()

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
		if not joining_date:
			joining_date, relieving_date = frappe.db.get_value("Employee", self.employee,
				["date_of_joining", "relieving_date"])

		holidays = self.get_holidays_for_employee(self.start_date, self.end_date)
		working_days = date_diff(self.end_date, self.start_date) + 1
		if not cint(frappe.db.get_value("HR Settings", None, "include_holidays_in_total_working_days")):
			working_days -= len(holidays)
			if working_days < 0:
				frappe.throw(_("There are more holidays than working days this month."))

		actual_lwp = self.calculate_lwp(holidays, working_days)
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
		for d in self.get(component_type):
			if cint(d.depends_on_lwp) == 1 and not self.salary_slip_based_on_timesheet:
				d.amount = rounded((flt(d.default_amount) * flt(self.payment_days)
					/ cint(self.total_working_days)), self.precision("amount", component_type))
			elif not self.payment_days and not self.salary_slip_based_on_timesheet:
				d.amount = 0
			elif not d.amount:
				d.amount = d.default_amount
			self.set(total_field, self.get(total_field) + flt(d.amount))

	def calculate_net_pay(self):
		if self.salary_structure:
			self.calculate_component_amounts()

		disable_rounded_total = cint(frappe.db.get_value("Global Defaults", None, "disable_rounded_total"))

		self.gross_pay = flt(self.arrear_amount) + flt(self.leave_encashment_amount)
		self.total_deduction = 0

		self.sum_components('earnings', 'gross_pay')
		self.sum_components('deductions', 'total_deduction')

		self.net_pay = flt(self.gross_pay) - flt(self.total_deduction)
		self.rounded_total = rounded(self.net_pay,
			self.precision("net_pay") if disable_rounded_total else 0)

	def on_submit(self):
		if self.net_pay < 0:
			frappe.throw(_("Net Pay cannot be less than 0"))
		else:
			self.set_status()
			self.update_status(self.name)
			if(frappe.db.get_single_value("HR Settings", "email_salary_slip_to_employee")):
				self.email_salary_slip()

	def on_cancel(self):
		self.set_status()
		self.update_status()

	def email_salary_slip(self):
		receiver = frappe.db.get_value("Employee", self.employee, "prefered_email")

		if receiver:
			subj = 'Salary Slip - from {0} to {1}'.format(self.start_date, self.end_date)
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
			if self.journal_entry:
				status = "Paid"
		elif self.docstatus == 2:
			status = "Cancelled"
		return status

def unlink_ref_doc_from_salary_slip(ref_no):
	linked_ss = frappe.db.sql_list("""select name from `tabSalary Slip`
	where journal_entry=%s and docstatus < 2""", (ref_no))
	if linked_ss:
		for ss in linked_ss:
			ss_doc = frappe.get_doc("Salary Slip", ss)
			frappe.db.set_value("Salary Slip", ss_doc.name, "status", "Submitted")
			frappe.db.set_value("Salary Slip", ss_doc.name, "journal_entry", "")


def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	employees = frappe.get_list("Employee", fields=["name"], filters={'user_id': user}, ignore_permissions=True)
	if employees:
		query = ""
		employee = frappe.get_doc('Employee', {'name': employees[0].name})
		
		if u'Employee' in frappe.get_roles(user):
			if query != "":
				query+=" or "
			query+=""" employee = '{0}'""".format(employee.name)
		if u'HR Specialist' in frappe.get_roles(user) or u'HR Manager' in frappe.get_roles(user):
			query=""
		return query

