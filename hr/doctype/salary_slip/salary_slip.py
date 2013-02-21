# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import add_days, cint, cstr, flt, getdate
from webnotes.model.doc import make_autoname
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint
from setup.utils import get_company_currency

sql = webnotes.conn.sql
	
from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist
		
		
	def autoname(self):
		self.doc.name = make_autoname('Sal Slip/' +self.doc.employee + '/.#####') 


	def get_emp_and_leave_details(self):
		if self.doc.employee:
			# Get payment days
			if self.doc.fiscal_year and self.doc.month:
				self.get_leave_details()

			# check sal structure
			struct = self.check_sal_struct()
			if struct:
				self.pull_sal_struct(struct)


	def check_sal_struct(self):
		struct = sql("select name from `tabSalary Structure` where employee ='%s' and is_active = 'Yes' "%self.doc.employee)
		if not struct:
			msgprint("Please create Salary Structure for employee '%s'"%self.doc.employee)
			self.doc.employee = ''
		return struct and struct[0][0] or ''


	def pull_sal_struct(self, struct):
		self.doclist = self.doc.clear_table(self.doclist, 'earning_details')
		self.doclist = self.doc.clear_table(self.doclist, 'deduction_details')

		get_obj('DocType Mapper', 'Salary Structure-Salary Slip').dt_map('Salary Structure', 'Salary Slip', struct, self.doc, self.doclist, "[['Salary Structure', 'Salary Slip'],['Salary Structure Earning', 'Salary Slip Earning'],['Salary Structure Deduction','Salary Slip Deduction']]")

		basic_info = sql("select bank_name, bank_ac_no, esic_card_no, pf_number from `tabEmployee` where name ='%s'" % self.doc.employee)
		self.doc.bank_name = basic_info[0][0]
		self.doc.bank_account_no = basic_info[0][1]
		self.doc.esic_no = basic_info[0][2]
		self.doc.pf_no = basic_info[0][3]


	def get_leave_details(self, lwp=None):
		m = get_obj('Salary Manager').get_month_details(self.doc.fiscal_year, self.doc.month)
		
		if not lwp:
			lwp = self.calculate_lwp(m)
		self.doc.total_days_in_month = m['month_days']
		self.doc.leave_without_pay = lwp
		payment_days = flt(self.get_payment_days(m)) - flt(lwp)
		self.doc.payment_days = payment_days > 0 and payment_days or 0
		

	def get_payment_days(self, m):
		payment_days = m['month_days']
		emp = webnotes.conn.sql("select date_of_joining, relieving_date from `tabEmployee` \
			where name = %s", self.doc.employee, as_dict=1)[0]
			
		if emp['relieving_date']:
			if getdate(emp['relieving_date']) > m['month_start_date'] and getdate(emp['relieving_date']) < m['month_end_date']:
				payment_days = getdate(emp['relieving_date']).day
			elif getdate(emp['relieving_date']) < m['month_start_date']:
				payment_days = 0
			
		if emp['date_of_joining']:
			if getdate(emp['date_of_joining']) > m['month_start_date'] and getdate(emp['date_of_joining']) < m['month_end_date']:
				payment_days = payment_days - getdate(emp['date_of_joining']).day + 1
			elif getdate(emp['date_of_joining']) > m['month_end_date']:
				payment_days = 0

		return payment_days




	def calculate_lwp(self, m):
		holidays = sql("select t1.holiday_date from `tabHoliday` t1, tabEmployee t2 where t1.parent = t2.holiday_list and t2.name = '%s' and t1.holiday_date between '%s' and '%s'" % (self.doc.employee, m['month_start_date'], m['month_end_date']))
		if not holidays:
			holidays = sql("select t1.holiday_date from `tabHoliday` t1, `tabHoliday List` t2 where t1.parent = t2.name and ifnull(t2.is_default, 0) = 1 and t2.fiscal_year = '%s'" % self.doc.fiscal_year)
		holidays = [cstr(i[0]) for i in holidays]
		lwp = 0
		for d in range(m['month_days']):
			dt = add_days(cstr(m['month_start_date']), d)
			if dt not in holidays:
				leave = sql("""
					select t1.name, t1.half_day
					from `tabLeave Application` t1, `tabLeave Type` t2 
					where t2.name = t1.leave_type 
					and ifnull(t2.is_lwp, 0) = 1 
					and t1.docstatus = 1 
					and t1.employee = '%s' 
					and '%s' between from_date and to_date
				"""%(self.doc.employee, dt))
				if leave:
					lwp = cint(leave[0][1]) and lwp + 0.5 or lwp + 1
		return lwp
					

	def check_existing(self):
		ret_exist = sql("select name from `tabSalary Slip` where month = '%s' and fiscal_year = '%s' and docstatus != 2 and employee = '%s' and name !='%s'" % (self.doc.month,self.doc.fiscal_year,self.doc.employee,self.doc.name))
		if ret_exist:
			msgprint("Salary Slip of employee '%s' already created for this month" % self.doc.employee)
			self.doc.employee = ''
			raise Exception


	def validate(self):
		from webnotes.utils import money_in_words
		self.check_existing()
		company_currency = get_company_currency(self.doc.company)
		self.doc.total_in_words = money_in_words(self.doc.rounded_total, company_currency)


	def calculate_earning_total(self):
		"""
			Calculates total earnings considering lwp
		"""
		self.doc.gross_pay = flt(self.doc.arrear_amount) + flt(self.doc.leave_encashment_amount)
		for d in getlist(self.doclist, 'earning_details'):
			if cint(d.e_depends_on_lwp) == 1:
				d.e_modified_amount = round(flt(d.e_amount)*flt(self.doc.payment_days)/cint(self.doc.total_days_in_month), 2)
			elif not self.doc.payment_days:
				d.e_modified_amount = 0
			self.doc.gross_pay += d.e_modified_amount
	
	def calculate_ded_total(self):
		"""
			Calculates total deduction considering lwp
		"""
		self.doc.total_deduction = 0
		for d in getlist(self.doclist, 'deduction_details'):
			if cint(d.d_depends_on_lwp) == 1:
				d.d_modified_amount = round(flt(d.d_amount)*flt(self.doc.payment_days)/cint(self.doc.total_days_in_month), 2)
			elif not self.doc.payment_days:
				d.d_modified_amount = 0
			
			self.doc.total_deduction += d.d_modified_amount
				
	def calculate_net_pay(self):
		"""
			Calculate net payment
		"""
		self.calculate_earning_total()
		self.calculate_ded_total()
		self.doc.net_pay = flt(self.doc.gross_pay) - flt(self.doc.total_deduction)
		self.doc.rounded_total = round(self.doc.net_pay)
		

	def on_submit(self):
		if(self.doc.email_check == 1):			
			self.send_mail_funct()
			

	def send_mail_funct(self):	 
		from webnotes.utils.email_lib import sendmail
		emailid_ret=sql("select company_email from `tabEmployee` where name = '%s'"%self.doc.employee)
		if emailid_ret:
			receiver = cstr(emailid_ret[0][0]) 
			subj = 'Salary Slip - ' + cstr(self.doc.month) +'/'+cstr(self.doc.fiscal_year)
			earn_ret=sql("select e_type,e_modified_amount from `tabSalary Slip Earning` where parent = '%s'"%self.doc.name)
			ded_ret=sql("select d_type,d_modified_amount from `tabSalary Slip Deduction` where parent = '%s'"%self.doc.name)
		 
			earn_table = ''
			ded_table = ''
			if earn_ret:			
				earn_table += "<table cellspacing=5px cellpadding=5px width='100%%'>"
				
				for e in earn_ret:
					if not e[1]:
						earn_table +='<tr><td>%s</td><td align="right">0.00</td></tr>'%(cstr(e[0]))
					else:
						earn_table +='<tr><td>%s</td><td align="right">%s</td></tr>'%(cstr(e[0]),cstr(e[1]))
				earn_table += '</table>'
			
			if ded_ret:
			
				ded_table += "<table cellspacing=5px cellpadding=5px width='100%%'>"
				
				for d in ded_ret:
					if not d[1]:
						ded_table +='<tr><td">%s</td><td align="right">0.00</td></tr>'%(cstr(d[0]))
					else:
						ded_table +='<tr><td>%s</td><td align="right">%s</td></tr>'%(cstr(d[0]),cstr(d[1]))
				ded_table += '</table>'
			
			letter_head = sql("select value from `tabSingles` where field = 'letter_head' and doctype = 'Control Panel'")
			
			if not letter_head:
				letter_head = ''
			
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
					<td colspan = 2 width = "50%%" bgcolor="#CCC" align="center"><b>Earnings</b></td>
					<td colspan = 2 width = "50%%" bgcolor="#CCC" align="center"><b>Deductions</b></td>
				</tr>
				<tr>
					<td colspan = 2 width = "50%%" valign= "top">%s</td>
					<td colspan = 2 width = "50%%" valign= "top">%s</td>
				</tr>
			</table>
			<table cellspacing= "5" cellpadding="5" width = '100%%'>
				<tr>
					<td width = '25%%'><b>Gross Pay :</b> </td><td width = '25%%' align='right'>%s</td>
					<td width = '25%%'><b>Total Deduction :</b></td><td width = '25%%' align='right'> %s</td>
				</tr>
				<tr>
					<tdwidth='25%%'><b>Net Pay : </b></td><td width = '25%%' align='right'><b>%s</b></td>
					<td colspan = '2' width = '50%%'></td>
				</tr>
				<tr>
					<td width='25%%'><b>Net Pay(in words) : </td><td colspan = '3' width = '50%%'>%s</b></td>
				</tr>
			</table></div>'''%(cstr(letter_head[0][0]),cstr(self.doc.employee), cstr(self.doc.employee_name), cstr(self.doc.month), cstr(self.doc.fiscal_year), cstr(self.doc.department), cstr(self.doc.branch), cstr(self.doc.designation), cstr(self.doc.grade), cstr(self.doc.bank_account_no), cstr(self.doc.bank_name), cstr(self.doc.arrear_amount), cstr(self.doc.payment_days), earn_table, ded_table, cstr(flt(self.doc.gross_pay)), cstr(flt(self.doc.total_deduction)), cstr(flt(self.doc.net_pay)), cstr(self.doc.total_in_words))
			sendmail([receiver], subject=subj, msg = msg)
		else:
			msgprint("Company Email ID not found, hence mail not sent")
