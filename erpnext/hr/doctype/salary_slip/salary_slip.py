# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
import datetime

from frappe.utils import cint, cstr, flt, getdate, rounded, date_diff, money_in_words, getdate
from frappe.model.naming import make_autoname

from frappe import msgprint, _
from erpnext.hr.doctype.payroll_entry.payroll_entry import get_start_end_dates
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.utilities.transaction_base import TransactionBase
from frappe.utils.background_jobs import enqueue
from erpnext.hr.doctype.additional_salary.additional_salary import get_additional_salary_component
from erpnext.hr.utils import get_payroll_period, calculate_leaves
from erpnext.hr.doctype.employee_benefit_application.employee_benefit_application import get_benefit_component_amount
from erpnext.hr.doctype.employee_benefit_claim.employee_benefit_claim import get_benefit_claim_amount, get_last_payroll_period_benefits

class NegativeSalaryError(frappe.ValidationError): pass

class SalarySlip(TransactionBase):
	def __init__(self, *args, **kwargs):
		super(SalarySlip, self).__init__(*args, **kwargs)
		self.series = 'Sal Slip/{0}/.#####'.format(self.employee)
		self.whitelisted_globals = {
			"int": int,
			"float": float,
			"long": int,
			"round": round,
			"date": datetime.date,
			"getdate": getdate
		}

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

				if key=="earnings" and struct_row.is_flexible_benefit == 1:
					self.add_employee_flexi_benefits(struct_row)

		additional_components = get_additional_salary_component(self.employee, self.start_date, self.end_date)
		if additional_components:
			for additional_component in additional_components:
				additional_component = frappe._dict(additional_component)
				amount = additional_component.amount
				overwrite = additional_component.overwrite
				key = "earnings"
				if additional_component.type == "Deduction":
					key = "deductions"
				self.update_component_row(frappe._dict(additional_component.struct_row), amount, key, overwrite=overwrite)

		self.get_last_payroll_period_benefit()

		# Calculate variable_based_on_taxable_salary after all components updated in salary slip
		for struct_row in self._salary_structure_doc.get("deductions"):
			if struct_row.variable_based_on_taxable_salary == 1 and not struct_row.formula and not struct_row.amount:
				tax_detail = self.calculate_variable_based_on_taxable_salary(struct_row.salary_component)
				if tax_detail and tax_detail[1]:
					self.update_component_row(frappe._dict(tax_detail[0]), tax_detail[1], "deductions", tax_detail[2], tax_detail[3])

	def get_last_payroll_period_benefit(self):
		payroll_period = get_payroll_period(self.start_date, self.end_date, self.company)
		if payroll_period:
			# Check for last payroll period
			if (getdate(payroll_period.end_date) <= getdate(self.end_date)):
				current_flexi_amount = 0
				for d in self.get("earnings"):
					if d.is_flexible_benefit == 1:
						current_flexi_amount += d.amount
				last_benefits = get_last_payroll_period_benefits(self.employee, self.start_date, self.end_date,\
				 current_flexi_amount, payroll_period, self._salary_structure_doc)
				if last_benefits:
					for last_benefit in last_benefits:
						last_benefit = frappe._dict(last_benefit)
						amount = last_benefit.amount
						self.update_component_row(frappe._dict(last_benefit.struct_row), amount, "earnings")

	def add_employee_flexi_benefits(self, struct_row):
		if frappe.db.get_value("Salary Component", struct_row.salary_component, "pay_against_benefit_claim") != 1:
			benefit_component_amount = get_benefit_component_amount(self.employee, self.start_date, self.end_date, \
			struct_row, self._salary_structure_doc, self.total_working_days, self.payroll_frequency)
			if benefit_component_amount:
				self.update_component_row(struct_row, benefit_component_amount, "earnings")
		else:
			benefit_claim_amount = get_benefit_claim_amount(self.employee, self.start_date, self.end_date, struct_row.salary_component)
			if benefit_claim_amount:
				self.update_component_row(struct_row, benefit_claim_amount, "earnings")

	def update_component_row(self, struct_row, amount, key, benefit_tax=None, additional_tax=None, overwrite=1):
		component_row = None
		for d in self.get(key):
			if d.salary_component == struct_row.salary_component:
				component_row = d
		if not component_row:
			self.append(key, {
				'amount': amount,
				'default_amount': amount,
				'depends_on_lwp' : struct_row.depends_on_lwp,
				'prorated_based_on_attendance': struct_row.prorated_based_on_attendance,
				'salary_component' : struct_row.salary_component,
				'abbr' : struct_row.abbr,
				'do_not_include_in_total' : struct_row.do_not_include_in_total,
				'is_tax_applicable': struct_row.is_tax_applicable,
				'is_flexible_benefit': struct_row.is_flexible_benefit,
				'variable_based_on_taxable_salary': struct_row.variable_based_on_taxable_salary,
				'is_additional_component': struct_row.is_additional_component,
				'tax_on_flexible_benefit': benefit_tax,
				'tax_on_additional_salary': additional_tax,
				'bank': struct_row.get("bank")
			})
		else:
			if overwrite:
				component_row.default_amount = amount
				component_row.amount = amount
			else:
				component_row.default_amount += amount
				component_row.amount = component_row.default_amount

			component_row.tax_on_flexible_benefit = benefit_tax
			component_row.tax_on_additional_salary = additional_tax

	def eval_condition_and_formula(self, d, data):
		try:
			condition = d.condition.strip() if d.condition else None
			if condition:
				if not frappe.safe_eval(condition, self.whitelisted_globals, data):
					return None
			amount = d.amount
			if d.amount_based_on_formula:
				formula = d.formula.strip() if d.formula else None
				if formula:
					amount = rounded(frappe.safe_eval(formula, self.whitelisted_globals, data))
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

		data.update(frappe.get_doc("Salary Structure Assignment",
			{"employee": self.employee, "salary_structure": self.salary_structure}).as_dict())

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
		cond = """and sa.employee=%(employee)s and (sa.from_date <= %(start_date)s or
				sa.from_date <= %(end_date)s or sa.from_date <= %(joining_date)s)"""
		if self.payroll_frequency:
			cond += """and ss.payroll_frequency = '%(payroll_frequency)s'""" % {"payroll_frequency": self.payroll_frequency}

		st_name = frappe.db.sql("""
			select sa.salary_structure
			from `tabSalary Structure Assignment` sa join `tabSalary Structure` ss
			where sa.salary_structure=ss.name
				and sa.docstatus = 1 and ss.docstatus = 1 and ss.is_active ='Yes' %s
			order by sa.from_date desc
			limit 1
		""" %cond, {'employee': self.employee, 'start_date': self.start_date,
			'end_date': self.end_date, 'joining_date': joining_date})

		if st_name:
			self.salary_structure = st_name[0][0]
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

	def get_leave_details(self, joining_date=None, relieving_date=None, lwp=None):
		if not joining_date:
			joining_date, relieving_date = frappe.db.get_value("Employee", self.employee,
				["date_of_joining", "relieving_date"])

		holidays = self.get_holidays_for_employee(self.start_date, self.end_date)
		working_days = date_diff(self.end_date, self.start_date) + 1
		total_leaves, actual_lwp = calculate_leaves(self.employee, self.start_date, holidays, working_days)

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
		self.total_leaves = total_leaves

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
			if (self.salary_structure
				and (cint(d.depends_on_lwp) or cint(d.prorated_based_on_attendance))
				and (not
				    self.salary_slip_based_on_timesheet or
					getdate(self.start_date) < joining_date or
					getdate(self.end_date) > relieving_date
				)):

				payment_days = flt(self.payment_days)
				if cint(d.prorated_based_on_attendance):
					payment_days = cint(self.total_working_days) - flt(self.total_leaves)

				d.amount = rounded((flt(d.default_amount) * flt(payment_days) / cint(self.total_working_days)))
			elif not self.payment_days and not self.salary_slip_based_on_timesheet and \
				cint(d.depends_on_lwp):
				d.amount = 0
			elif not d.amount:
				d.amount = d.default_amount
			if not d.do_not_include_in_total:
				self.set(total_field, self.get(total_field) + flt(d.amount))

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

		if self.net_pay < 0:
			frappe.throw(_("Net Pay cannnot be negative"), NegativeSalaryError)

	def set_loan_repayment(self):
		self.set('loans', [])
		self.total_loan_repayment = 0
		self.total_interest_amount = 0
		self.total_principal_amount = 0

		for loan in self.get_loan_details():
			self.append('loans', {
				'loan': loan.name,
				'total_payment': loan.total_payment,
				'interest_amount': loan.interest_amount,
				'principal_amount': loan.principal_amount,
				'loan_account': loan.loan_account,
				'interest_income_account': loan.interest_income_account
			})

			self.total_loan_repayment += loan.total_payment
			self.total_interest_amount += loan.interest_amount
			self.total_principal_amount += loan.principal_amount

	def get_loan_details(self):
		return frappe.db.sql("""select rps.principal_amount, rps.interest_amount, l.name,
				rps.total_payment, l.loan_account, l.interest_income_account
			from
				`tabRepayment Schedule` as rps, `tabLoan` as l
			where
				l.name = rps.parent and rps.payment_date between %s and %s and
				l.repay_from_salary = 1 and l.docstatus = 1 and l.applicant = %s""",
			(self.start_date, self.end_date, self.employee), as_dict=True) or []

	def on_submit(self):
		if self.net_pay < 0:
			frappe.throw(_("Net Pay cannot be less than 0"))
		else:
			self.set_status()
			self.update_status(self.name)
			self.update_salary_slip_in_additional_salary()
			if (frappe.db.get_single_value("HR Settings", "email_salary_slip_to_employee")) and not frappe.flags.via_payroll_entry:
				self.email_salary_slip()

	def on_cancel(self):
		self.set_status()
		self.update_status()
		self.update_salary_slip_in_additional_salary()

	def on_trash(self):
		from frappe.model.naming import revert_series_if_last
		revert_series_if_last(self.series, self.name)

	def update_salary_slip_in_additional_salary(self):
		salary_slip = self.name if self.docstatus==1 else None
		frappe.db.sql("""
			update `tabAdditional Salary` set salary_slip=%s
			where employee=%s and docstatus=1
				and payroll_date between %s and %s
		""", (salary_slip, self.employee, self.start_date, self.end_date))

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
			if not frappe.flags.in_test:
				enqueue(method=frappe.sendmail, queue='short', timeout=300, is_async=True, **email_args)
			else:
				frappe.sendmail(**email_args)
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

	def calculate_variable_based_on_taxable_salary(self, tax_component):
		payroll_period = get_payroll_period(self.start_date, self.end_date, self.company)
		if not payroll_period:
			frappe.msgprint(_("Start and end dates not in a valid Payroll Period, cannot calculate {0}.")
				.format(tax_component))
			return False
		if payroll_period.end_date <= getdate(self.end_date):
			if not self.deduct_tax_for_unsubmitted_tax_exemption_proof or not\
				self.deduct_tax_for_unclaimed_employee_benefits:
				frappe.throw(_("You have to Deduct Tax for Unsubmitted Tax Exemption Proof and Unclaimed \
					Employee Benefits in the last Salary Slip of Payroll Period"))
		# calc prorata tax to be applied
		return self.calculate_variable_tax(tax_component, payroll_period)

	def calculate_variable_tax(self, tax_component, payroll_period):
		annual_taxable_earning, period_factor = 0, 0
		pro_rata_tax_paid, additional_tax_paid,  benefit_tax_paid = 0, 0, 0
		unclaimed_earning, unclaimed_benefit, additional_income = 0, 0, 0

		# get taxable_earning, additional_income in this slip
		taxable_earning = self.get_taxable_earnings()
		if self.deduct_tax_for_unclaimed_employee_benefits:
			# get all untaxed benefits till date, pass amount to be taxed by later methods
			unclaimed_benefit = self.calculate_unclaimed_taxable_benefit(payroll_period)
			# flexi's excluded from monthly tax, add flexis in this slip to unclaimed_benefit
			unclaimed_benefit += self.get_taxable_earnings(only_flexi=True)["taxable_earning"]
		if self.deduct_tax_for_unsubmitted_tax_exemption_proof:
			# do not consider exemption, calc tax to be paid for the period till date
			# considering prorata taxes paid and proofs submitted
			unclaimed_earning = self.calculate_unclaimed_taxable_earning(payroll_period, tax_component)
			earning_in_period = taxable_earning["taxable_earning"] + unclaimed_earning
			period_factor = self.get_period_factor(payroll_period.start_date, payroll_period.end_date,
								payroll_period.start_date, self.end_date)
			annual_taxable_earning = earning_in_period * period_factor
			additional_income += self.get_total_additional_income(payroll_period.start_date)
		else:
			# consider exemption declaration, find annual_earning by monthly taxable salary
			period_factor = self.get_period_factor(payroll_period.start_date, payroll_period.end_date)
			annual_earning = taxable_earning["taxable_earning"] * period_factor
			exemption_amount = 0
			if frappe.db.exists("Employee Tax Exemption Declaration", {"employee": self.employee,
			"payroll_period": payroll_period.name, "docstatus": 1}):
				exemption_amount = frappe.db.get_value("Employee Tax Exemption Declaration",
					{"employee": self.employee, "payroll_period": payroll_period.name, "docstatus": 1},
					"total_exemption_amount")
			annual_taxable_earning = annual_earning - exemption_amount

		if self.deduct_tax_for_unclaimed_employee_benefits or self.deduct_tax_for_unsubmitted_tax_exemption_proof:
			tax_detail = self.get_tax_paid_in_period(payroll_period, tax_component)
			if tax_detail:
				pro_rata_tax_paid = tax_detail["total_tax_paid"] - tax_detail["additional_tax"] - tax_detail["benefit_tax"]
				additional_tax_paid = tax_detail["additional_tax"]
				benefit_tax_paid = tax_detail["benefit_tax"]

		# add any additional income in this slip
		additional_income += taxable_earning["additional_income"]
		args = {"payroll_period": payroll_period.name, "tax_component": tax_component,
				"annual_taxable_earning": annual_taxable_earning, "period_factor": period_factor,
				"unclaimed_benefit": unclaimed_benefit, "additional_income": additional_income,
				"pro_rata_tax_paid": pro_rata_tax_paid, "benefit_tax_paid": benefit_tax_paid,
				"additional_tax_paid": additional_tax_paid}
		return self.calculate_tax(args)

	def calculate_unclaimed_taxable_benefit(self, payroll_period):
		total_benefit, total_benefit_claim = 0, 0

		# get total sum of benefits paid
		sum_benefit = frappe.db.sql("""select sum(sd.amount) from `tabSalary Detail` sd join
					`tabSalary Slip` ss on sd.parent=ss.name where sd.parentfield='earnings'
					and sd.is_tax_applicable=1 and is_flexible_benefit=1 and ss.docstatus=1
					and ss.employee='{0}' and ss.start_date between '{1}' and '{2}' and
					ss.end_date between '{1}' and '{2}'""".format(self.employee,
					payroll_period.start_date, self.start_date))
		if sum_benefit and sum_benefit[0][0]:
			total_benefit = sum_benefit[0][0]

		# get total benefits claimed
		sum_benefit_claim = frappe.db.sql("""select sum(claimed_amount) from
		`tabEmployee Benefit Claim` where docstatus=1 and employee='{0}' and claim_date
		between '{1}' and '{2}'""".format(self.employee, payroll_period.start_date, self.end_date))
		if sum_benefit_claim and sum_benefit_claim[0][0]:
			total_benefit_claim = sum_benefit_claim[0][0]
		return total_benefit - total_benefit_claim

	def calculate_unclaimed_taxable_earning(self, payroll_period, tax_component):
		total_taxable_earning, total_exemption_amount = 0, 0
		# calc total taxable amount in period
		sum_taxable_earning = frappe.db.sql("""select sum(sd.amount) from `tabSalary Detail` sd join
					`tabSalary Slip` ss on sd.parent=ss.name where sd.parentfield='earnings'
					and sd.is_tax_applicable=1 and is_additional_component=0 and is_flexible_benefit=0
					and ss.docstatus=1 and ss.employee='{0}' and ss.start_date between '{1}' and '{2}'
					and ss.end_date between '{1}' and '{2}'""".format(self.employee,
					payroll_period.start_date, self.start_date))
		if sum_taxable_earning and sum_taxable_earning[0][0]:
			total_taxable_earning = sum_taxable_earning[0][0]

		# add up total Proof Submission
		sum_exemption = frappe.db.sql("""select sum(exemption_amount) from
		`tabEmployee Tax Exemption Proof Submission` where docstatus=1 and employee='{0}' and
		payroll_period='{1}' and submission_date between '{2}' and '{3}'""".format(self.employee,
		payroll_period.name, payroll_period.start_date, self.end_date))
		if sum_exemption and sum_exemption[0][0]:
			total_exemption_amount = sum_exemption[0][0]
		total_taxable_earning -= total_exemption_amount
		return total_taxable_earning

	def get_total_additional_income(self, from_date):
		total_additional_pay = 0
		sum_additional_earning = frappe.db.sql("""select sum(sd.amount) from `tabSalary Detail` sd join
					`tabSalary Slip` ss on sd.parent=ss.name where sd.parentfield='earnings'
					and sd.is_tax_applicable=1 and is_additional_component=1 and is_flexible_benefit=0
					and ss.docstatus=1 and ss.employee='{0}' and ss.start_date between '{1}' and '{2}'
					and ss.end_date between '{1}' and '{2}'""".format(self.employee,
					from_date, self.start_date))
		if sum_additional_earning and sum_additional_earning[0][0]:
			total_additional_pay = sum_additional_earning[0][0]
		return total_additional_pay

	def get_tax_paid_in_period(self, payroll_period, tax_component, only_total=False):
		# find total_tax_paid, tax paid for benefit, additional_salary
		sum_tax_paid = frappe.db.sql("""select sum(sd.amount), sum(tax_on_flexible_benefit),
			sum(tax_on_additional_salary)  from `tabSalary Detail` sd join `tabSalary Slip`
			ss on sd.parent=ss.name where sd.parentfield='deductions' and sd.salary_component='{3}'
			and sd.variable_based_on_taxable_salary=1 and ss.docstatus=1 and ss.employee='{0}'
			and ss.start_date between '{1}' and '{2}' and ss.end_date between '{1}' and
			'{2}'""".format(self.employee, payroll_period.start_date, self.start_date, tax_component))
		if sum_tax_paid and sum_tax_paid[0][0]:
			return {'total_tax_paid': sum_tax_paid[0][0], 'benefit_tax':sum_tax_paid[0][1], 'additional_tax': sum_tax_paid[0][2]}

	def get_taxable_earnings(self, include_flexi=0, only_flexi=0):
		taxable_earning = 0
		additional_income = 0
		for earning in self.earnings:
			if earning.is_tax_applicable:
				if earning.is_additional_component:
					additional_income += earning.amount
					continue
				if only_flexi:
					if earning.is_tax_applicable and earning.is_flexible_benefit:
						taxable_earning += earning.amount
					continue
				if include_flexi:
					if earning.is_tax_applicable or (earning.is_tax_applicable and earning.is_flexible_benefit):
						taxable_earning += earning.amount
				else:
					if earning.is_tax_applicable and not earning.is_flexible_benefit:
						taxable_earning += earning.amount
		return {"taxable_earning": taxable_earning, "additional_income": additional_income}

	def calculate_tax(self, args):
		tax_amount, benefit_tax, additional_tax = 0, 0, 0
		annual_taxable_earning = args.get("annual_taxable_earning")
		benefit_to_tax = args.get("unclaimed_benefit")
		additional_income = args.get("additional_income")
		# Get tax calc by period
		annual_tax = self.calculate_tax_by_tax_slab(args.get("payroll_period"), annual_taxable_earning)

		# Calc prorata tax
		tax_amount = annual_tax / args.get("period_factor")

		# Benefit is a part of Salary Structure, add the tax diff, update annual_tax
		if benefit_to_tax > 0:
			annual_taxable_earning += benefit_to_tax
			annual_tax_with_benefit_income = self.calculate_tax_by_tax_slab(
								args.get("payroll_period"), annual_taxable_earning)
			benefit_tax = annual_tax_with_benefit_income - annual_tax - args.get("benefit_tax_paid")
			tax_amount += benefit_tax
			annual_tax = annual_tax_with_benefit_income

		# find the annual tax diff caused by additional_income, add to tax_amount
		if additional_income > 0:
			annual_tax_with_additional_income = self.calculate_tax_by_tax_slab(
					args.get("payroll_period"), annual_taxable_earning + additional_income)
			additional_tax = annual_tax_with_additional_income - annual_tax - args.get("additional_tax_paid")
			tax_amount += additional_tax
		# less paid taxes
		if args.get("pro_rata_tax_paid"):
			tax_amount -= args.get("pro_rata_tax_paid")
		struct_row = self.get_salary_slip_row(args.get("tax_component"))
		return [struct_row, tax_amount, benefit_tax, additional_tax]

	def calculate_tax_by_tax_slab(self, payroll_period, annual_earning):
		payroll_period_obj = frappe.get_doc("Payroll Period", payroll_period)
		data = self.get_data_for_eval()
		taxable_amount = 0
		for slab in payroll_period_obj.taxable_salary_slabs:
			if slab.condition and not self.eval_tax_slab_condition(slab.condition, data):
				continue
			if not slab.to_amount and annual_earning > slab.from_amount:
				taxable_amount += (annual_earning - slab.from_amount) * slab.percent_deduction *.01
				continue
			if annual_earning > slab.from_amount and annual_earning < slab.to_amount:
				taxable_amount += (annual_earning - slab.from_amount) * slab.percent_deduction *.01
			elif annual_earning > slab.from_amount and annual_earning > slab.to_amount:
				taxable_amount += (slab.to_amount - slab.from_amount) * slab.percent_deduction * .01
		return taxable_amount

	def eval_tax_slab_condition(self, condition, data):
		try:
			condition = condition.strip()
			if condition:
				return frappe.safe_eval(condition, self.whitelisted_globals, data)
		except NameError as err:
			frappe.throw(_("Name error: {0}".format(err)))
		except SyntaxError as err:
			frappe.throw(_("Syntax error in condition: {0}".format(err)))
		except Exception as e:
			frappe.throw(_("Error in formula or condition: {0}".format(e)))
			raise

	def get_period_factor(self, period_start, period_end, start_date=None, end_date=None):
		# TODO if both deduct checked update the factor to make tax consistent
		payroll_days = date_diff(period_end, period_start) + 1
		if start_date and end_date:
			salary_days = date_diff(end_date, start_date) + 1
			return flt(payroll_days)/flt(salary_days)
		# if period configured for a year and monthly frequency return 12 to make tax calc consistent
		if 360 <= payroll_days <= 370 and self.payroll_frequency == "Monthly":
			return 12
		salary_days = date_diff(self.end_date, self.start_date) + 1
		return flt(payroll_days)/flt(salary_days)

	def get_salary_slip_row(self, salary_component):
		component = frappe.get_doc("Salary Component", salary_component)
		# Data for update_component_row
		struct_row = {}
		struct_row['depends_on_lwp'] = component.depends_on_lwp
		struct_row['prorated_based_on_attendance'] = component.prorated_based_on_attendance
		struct_row['salary_component'] = component.name
		struct_row['abbr'] = component.salary_component_abbr
		struct_row['do_not_include_in_total'] = component.do_not_include_in_total
		struct_row['is_tax_applicable'] = component.is_tax_applicable
		struct_row['is_flexible_benefit'] = component.is_flexible_benefit
		struct_row['variable_based_on_taxable_salary'] = component.variable_based_on_taxable_salary
		return struct_row

def unlink_ref_doc_from_salary_slip(ref_no):
	linked_ss = frappe.db.sql_list("""select name from `tabSalary Slip`
	where journal_entry=%s and docstatus < 2""", (ref_no))
	if linked_ss:
		for ss in linked_ss:
			ss_doc = frappe.get_doc("Salary Slip", ss)
			frappe.db.set_value("Salary Slip", ss_doc.name, "journal_entry", "")