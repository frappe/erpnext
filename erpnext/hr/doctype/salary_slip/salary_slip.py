# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate, _round
from frappe.model.naming import make_autoname

from frappe.model.code import get_obj
from frappe import msgprint, _
from erpnext.setup.utils import get_company_currency

	
from erpnext.utilities.transaction_base import TransactionBase

class SalarySlip(TransactionBase):
	def autoname(self):
		self.name = make_autoname('Sal Slip/' +self.employee + '/.#####') 

	def get_emp_and_leave_details(self):
		if self.employee:
			self.get_leave_details()
			struct = self.check_sal_struct()
			if struct:
				self.pull_sal_struct(struct)

	def check_sal_struct(self):
		struct = frappe.db.sql("""select name from `tabSalary Structure` 
			where employee=%s and is_active = 'Yes'""", self.employee)
		if not struct:
			msgprint("Please create Salary Structure for employee '%s'" % self.employee)
			self.employee = None
		return struct and struct[0][0] or ''

	def pull_sal_struct(self, struct):
		from erpnext.hr.doctype.salary_structure.salary_structure import get_mapped_doc
		self.doclist = get_mapped_doc(struct, self.doclist)
		
	def pull_emp_details(self):
		emp = frappe.db.get_value("Employee", self.employee, 
			["bank_name", "bank_ac_no", "esic_card_no", "pf_number"], as_dict=1)
		if emp:
			self.bank_name = emp.bank_name
			self.bank_account_no = emp.bank_ac_no
			self.esic_no = emp.esic_card_no
			self.pf_no = emp.pf_number

	def get_leave_details(self, lwp=None):
		if not self.fiscal_year:
			self.fiscal_year = frappe.get_default("fiscal_year")
		if not self.month:
			self.month = "%02d" % getdate(nowdate()).month
			
		m = get_obj('Salary Manager').get_month_details(self.fiscal_year, self.month)
		holidays = self.get_holidays_for_employee(m)
		
		if not cint(frappe.db.get_value("HR Settings", "HR Settings",
			"include_holidays_in_total_working_days")):
				m["month_days"] -= len(holidays)
				if m["month_days"] < 0:
					msgprint(_("Bummer! There are more holidays than working days this month."),
						raise_exception=True)
			
		if not lwp:
			lwp = self.calculate_lwp(holidays, m)
		self.total_days_in_month = m['month_days']
		self.leave_without_pay = lwp
		payment_days = flt(self.get_payment_days(m)) - flt(lwp)
		self.payment_days = payment_days > 0 and payment_days or 0
		

	def get_payment_days(self, m):
		payment_days = m['month_days']
		emp = frappe.db.sql("select date_of_joining, relieving_date from `tabEmployee` \
			where name = %s", self.employee, as_dict=1)[0]
			
		if emp['relieving_date']:
			if getdate(emp['relieving_date']) > m['month_start_date'] and \
				getdate(emp['relieving_date']) < m['month_end_date']:
					payment_days = getdate(emp['relieving_date']).day
			elif getdate(emp['relieving_date']) < m['month_start_date']:
				frappe.msgprint(_("Relieving Date of employee is ") + cstr(emp['relieving_date']
					+ _(". Please set status of the employee as 'Left'")), raise_exception=1)
				
			
		if emp['date_of_joining']:
			if getdate(emp['date_of_joining']) > m['month_start_date'] and \
				getdate(emp['date_of_joining']) < m['month_end_date']:
					payment_days = payment_days - getdate(emp['date_of_joining']).day + 1
			elif getdate(emp['date_of_joining']) > m['month_end_date']:
				payment_days = 0

		return payment_days
		
	def get_holidays_for_employee(self, m):
		holidays = frappe.db.sql("""select t1.holiday_date 
			from `tabHoliday` t1, tabEmployee t2 
			where t1.parent = t2.holiday_list and t2.name = %s 
			and t1.holiday_date between %s and %s""", 
			(self.employee, m['month_start_date'], m['month_end_date']))
		if not holidays:
			holidays = frappe.db.sql("""select t1.holiday_date 
				from `tabHoliday` t1, `tabHoliday List` t2 
				where t1.parent = t2.name and ifnull(t2.is_default, 0) = 1 
				and t2.fiscal_year = %s
				and t1.holiday_date between %s and %s""", (self.fiscal_year, 
					m['month_start_date'], m['month_end_date']))
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
					and ifnull(t2.is_lwp, 0) = 1 
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
			msgprint("Salary Slip of employee '%s' already created for this month" 
				% self.employee, raise_exception=1)


	def validate(self):
		from frappe.utils import money_in_words
		self.check_existing()
		
		if not (len(self.get("earning_details")) or 
			len(self.get("deduction_details"))):
				self.get_emp_and_leave_details()
		else:
			self.get_leave_details(self.leave_without_pay)

		if not self.net_pay:
			self.calculate_net_pay()
			
		company_currency = get_company_currency(self.company)
		self.total_in_words = money_in_words(self.rounded_total, company_currency)

	def calculate_earning_total(self):
		self.gross_pay = flt(self.arrear_amount) + flt(self.leave_encashment_amount)
		for d in self.get("earning_details"):
			if cint(d.e_depends_on_lwp) == 1:
				d.e_modified_amount = _round(flt(d.e_amount) * flt(self.payment_days)
					/ cint(self.total_days_in_month), 2)
			elif not self.payment_days:
				d.e_modified_amount = 0
			else:
				d.e_modified_amount = d.e_amount
			self.gross_pay += flt(d.e_modified_amount)
	
	def calculate_ded_total(self):
		self.total_deduction = 0
		for d in self.get('deduction_details'):
			if cint(d.d_depends_on_lwp) == 1:
				d.d_modified_amount = _round(flt(d.d_amount) * flt(self.payment_days) 
					/ cint(self.total_days_in_month), 2)
			elif not self.payment_days:
				d.d_modified_amount = 0
			else:
				d.d_modified_amount = d.d_amount
			
			self.total_deduction += flt(d.d_modified_amount)
				
	def calculate_net_pay(self):
		self.calculate_earning_total()
		self.calculate_ded_total()
		self.net_pay = flt(self.gross_pay) - flt(self.total_deduction)
		self.rounded_total = _round(self.net_pay)		

	def on_submit(self):
		if(self.email_check == 1):			
			self.send_mail_funct()
			

	def send_mail_funct(self):	 
		from frappe.utils.email_lib import sendmail
		receiver = frappe.db.get_value("Employee", self.employee, "company_email")
		if receiver:
			subj = 'Salary Slip - ' + cstr(self.month) +'/'+cstr(self.fiscal_year)
			earn_ret=frappe.db.sql("""select e_type, e_modified_amount from `tabSalary Slip Earning` 
				where parent = %s""", self.name)
			ded_ret=frappe.db.sql("""select d_type, d_modified_amount from `tabSalary Slip Deduction` 
				where parent = %s""", self.name)
		 
			earn_table = ''
			ded_table = ''
			if earn_ret:			
				earn_table += "<table cellspacing=5px cellpadding=5px width='100%%'>"
				
				for e in earn_ret:
					if not e[1]:
						earn_table += '<tr><td>%s</td><td align="right">0.00</td></tr>' % cstr(e[0])
					else:
						earn_table += '<tr><td>%s</td><td align="right">%s</td></tr>' \
							% (cstr(e[0]), cstr(e[1]))
				earn_table += '</table>'
			
			if ded_ret:
			
				ded_table += "<table cellspacing=5px cellpadding=5px width='100%%'>"
				
				for d in ded_ret:
					if not d[1]:
						ded_table +='<tr><td">%s</td><td align="right">0.00</td></tr>' % cstr(d[0])
					else:
						ded_table +='<tr><td>%s</td><td align="right">%s</td></tr>' \
							% (cstr(d[0]), cstr(d[1]))
				ded_table += '</table>'
			
			letter_head = frappe.db.get_value("Letter Head", {"is_default": 1, "disabled": 0}, 
				"content")
			
			msg = '''<div> %s <br>
			<table cellspacing= "5" cellpadding="5"  width = "100%%">
				<tr>
					<td width = "100%%" colspan = "2"><h4>Salary Slip</h4></td>
				</tr>
				<tr>
					<td width = "50%%"><b>Employee Code : %s</b></td>
					<td width = "50%%"><b>Employee Name : %s</b></td>
				</tr>
				<tr>
					<td width = "50%%">Month : %s</td>
					<td width = "50%%">Fiscal Year : %s</td>
				</tr>
				<tr>
					<td width = "50%%">Department : %s</td>
					<td width = "50%%">Branch : %s</td>
				</tr>
				<tr>
					<td width = "50%%">Designation : %s</td>
					<td width = "50%%">Grade : %s</td>
				</tr>
				<tr>				
					<td width = "50%%">Bank Account No. : %s</td>
					<td  width = "50%%">Bank Name : %s</td>
				
				</tr>
				<tr>
					<td  width = "50%%">Arrear Amount : <b>%s</b></td>
					<td  width = "50%%">Payment days : %s</td>
				
				</tr>
			</table>
			<table border="1px solid #CCC" width="100%%" cellpadding="0px" cellspacing="0px">
				<tr>
					<td colspan = 2 width = "50%%" bgcolor="#CCC" align="center">
						<b>Earnings</b></td>
					<td colspan = 2 width = "50%%" bgcolor="#CCC" align="center">
						<b>Deductions</b></td>
				</tr>
				<tr>
					<td colspan = 2 width = "50%%" valign= "top">%s</td>
					<td colspan = 2 width = "50%%" valign= "top">%s</td>
				</tr>
			</table>
			<table cellspacing= "5" cellpadding="5" width = '100%%'>
				<tr>
					<td width = '25%%'><b>Gross Pay :</b> </td>
					<td width = '25%%' align='right'>%s</td>
					<td width = '25%%'><b>Total Deduction :</b></td>
					<td width = '25%%' align='right'> %s</td>
				</tr>
				<tr>
					<tdwidth='25%%'><b>Net Pay : </b></td>
					<td width = '25%%' align='right'><b>%s</b></td>
					<td colspan = '2' width = '50%%'></td>
				</tr>
				<tr>
					<td width='25%%'><b>Net Pay(in words) : </td>
					<td colspan = '3' width = '50%%'>%s</b></td>
				</tr>
			</table></div>''' % (cstr(letter_head), cstr(self.employee), 
				cstr(self.employee_name), cstr(self.month), cstr(self.fiscal_year), 
				cstr(self.department), cstr(self.branch), cstr(self.designation), 
				cstr(self.grade), cstr(self.bank_account_no), cstr(self.bank_name), 
				cstr(self.arrear_amount), cstr(self.payment_days), earn_table, ded_table, 
				cstr(flt(self.gross_pay)), cstr(flt(self.total_deduction)), 
				cstr(flt(self.net_pay)), cstr(self.total_in_words))

			sendmail([receiver], subject=subj, msg = msg)
		else:
			msgprint("Company Email ID not found, hence mail not sent")
